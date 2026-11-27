"""Tokens de uso único enviados por e-mail: verificação de e-mail e recuperação de senha."""

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.erros import DadosRecusados
from app.modelos import FinalidadeToken, TokenConta, Usuario

VALIDADE = {
    FinalidadeToken.VERIFICACAO_EMAIL: timedelta(hours=24),
    FinalidadeToken.RECUPERACAO_SENHA: timedelta(minutes=30),
}


class TokenContaInvalido(DadosRecusados):
    """Mesma mensagem para inexistente, expirado, já usado ou de outra finalidade."""


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class ServicoTokensConta:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def emitir(self, usuario: Usuario, finalidade: FinalidadeToken) -> str:
        """Cria um token novo e invalida os anteriores da mesma finalidade (só o último vale)."""
        self._sessao.execute(
            update(TokenConta)
            .where(
                TokenConta.usuario_id == usuario.id,
                TokenConta.finalidade == finalidade,
                TokenConta.usado_em.is_(None),
            )
            .values(usado_em=func.now())
        )
        token = secrets.token_urlsafe(32)  # 256 bits
        self._sessao.add(
            TokenConta(
                usuario_id=usuario.id,
                finalidade=finalidade,
                token_hash=_hash(token),
                email_alvo=usuario.email
                if finalidade is FinalidadeToken.VERIFICACAO_EMAIL
                else None,
                expira_em=func.now() + VALIDADE[finalidade],
            )
        )
        self._sessao.commit()
        return token

    def dono(self, token: str, finalidade: FinalidadeToken) -> Usuario:
        """Só consulta (sem consumir): permite validar a nova senha antes de gastar o link."""
        registro = self._sessao.scalars(
            select(TokenConta).where(
                TokenConta.token_hash == _hash(token),
                TokenConta.finalidade == finalidade,
                TokenConta.usado_em.is_(None),
                TokenConta.expira_em > func.now(),
            )
        ).one_or_none()
        usuario = self._sessao.get(Usuario, registro.usuario_id) if registro else None
        if usuario is None or not usuario.ativo:
            raise TokenContaInvalido("Este link é inválido ou expirou. Peça um novo.")
        return usuario

    def consumir(self, token: str, finalidade: FinalidadeToken) -> tuple[Usuario, TokenConta]:
        """Marca o token como usado e devolve o dono. A trava impede o uso duplo simultâneo."""
        registro = self._sessao.scalars(
            select(TokenConta)
            .where(
                TokenConta.token_hash == _hash(token),
                TokenConta.finalidade == finalidade,
                TokenConta.usado_em.is_(None),
                TokenConta.expira_em > func.now(),
            )
            .with_for_update()
        ).one_or_none()
        usuario = self._sessao.get(Usuario, registro.usuario_id) if registro else None
        if registro is None or usuario is None or not usuario.ativo:
            self._sessao.rollback()
            raise TokenContaInvalido("Este link é inválido ou expirou. Peça um novo.")
        registro.usado_em = func.now()
        return usuario, registro
