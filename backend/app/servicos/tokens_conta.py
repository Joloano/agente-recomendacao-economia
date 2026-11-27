"""Tokens de uso único enviados por e-mail: verificação de e-mail e recuperação de senha.

Cada token fica preso ao endereço para o qual foi enviado (`email_alvo`): se o e-mail da conta
muda, os links antigos deixam de valer.
"""

import hashlib
import random
import secrets
from datetime import timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.erros import DadosRecusados
from app.modelos import FinalidadeToken, TokenConta, Usuario

VALIDADE = {
    FinalidadeToken.VERIFICACAO_EMAIL: timedelta(hours=24),
    FinalidadeToken.RECUPERACAO_SENHA: timedelta(minutes=30),
}
CHANCE_LIMPEZA = 0.05
MENSAGEM_INVALIDO = "Este link é inválido ou expirou. Peça um novo."


class TokenContaInvalido(DadosRecusados):
    """Mesma mensagem para inexistente, expirado, já usado ou de outra finalidade."""


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class ServicoTokensConta:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def emitir(self, usuario: Usuario, finalidade: FinalidadeToken, email_alvo: str) -> str:
        """Cria um token para `email_alvo` e invalida os anteriores da mesma finalidade.

        A linha do usuário é travada: dois pedidos simultâneos não deixam dois links válidos.
        """
        self._sessao.execute(select(Usuario.id).where(Usuario.id == usuario.id).with_for_update())
        self.invalidar(usuario, finalidade, confirmar=False)
        token = secrets.token_urlsafe(32)  # 256 bits
        self._sessao.add(
            TokenConta(
                usuario_id=usuario.id,
                finalidade=finalidade,
                token_hash=_hash(token),
                email_alvo=email_alvo,
                expira_em=func.now() + VALIDADE[finalidade],
            )
        )
        if random.random() < CHANCE_LIMPEZA:  # noqa: S311 - não é uso criptográfico
            self._sessao.execute(
                delete(TokenConta).where(TokenConta.expira_em < func.now() - timedelta(days=1))
            )
        self._sessao.commit()
        return token

    def invalidar(
        self, usuario: Usuario, finalidade: FinalidadeToken | None = None, *, confirmar: bool = True
    ) -> None:
        """Invalida os links pendentes (de uma finalidade ou de todas)."""
        condicoes = [TokenConta.usuario_id == usuario.id, TokenConta.usado_em.is_(None)]
        if finalidade is not None:
            condicoes.append(TokenConta.finalidade == finalidade)
        self._sessao.execute(update(TokenConta).where(*condicoes).values(usado_em=func.now()))
        if confirmar:
            self._sessao.commit()

    def _buscar(
        self, token: str, finalidade: FinalidadeToken, *, travar: bool
    ) -> TokenConta | None:
        consulta = select(TokenConta).where(
            TokenConta.token_hash == _hash(token),
            TokenConta.finalidade == finalidade,
            TokenConta.usado_em.is_(None),
            TokenConta.expira_em > func.now(),
        )
        if travar:
            consulta = consulta.with_for_update()
        return self._sessao.scalars(consulta).one_or_none()

    def dono(self, token: str, finalidade: FinalidadeToken) -> Usuario:
        """Só consulta (sem consumir): permite validar a nova senha antes de gastar o link."""
        registro = self._buscar(token, finalidade, travar=False)
        usuario = self._sessao.get(Usuario, registro.usuario_id) if registro else None
        if registro is None or usuario is None or not usuario.ativo:
            raise TokenContaInvalido(MENSAGEM_INVALIDO)
        return usuario

    def consumir(self, token: str, finalidade: FinalidadeToken) -> tuple[Usuario, TokenConta]:
        """Marca o token como usado e devolve o dono. A trava impede o uso duplo simultâneo."""
        registro = self._buscar(token, finalidade, travar=True)
        usuario = self._sessao.get(Usuario, registro.usuario_id) if registro else None
        if registro is None or usuario is None or not usuario.ativo:
            self._sessao.rollback()
            raise TokenContaInvalido(MENSAGEM_INVALIDO)
        registro.usado_em = func.now()
        return usuario, registro
