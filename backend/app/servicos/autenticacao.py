"""Casos de uso de conta: cadastro e login."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.erros import NaoAutenticado
from app.core.seguranca import gerar_hash, precisa_rehash, verificar_senha
from app.esquemas.autenticacao import RegistroEntrada, normalizar_email
from app.modelos import Papel, Usuario
from app.servicos.usuarios import SenhaRecusada, ServicoUsuarios

__all__ = ["CredenciaisInvalidas", "SenhaRecusada", "ServicoAutenticacao"]

MENSAGEM_LOGIN_INVALIDO = "E-mail ou senha incorretos."


class CredenciaisInvalidas(NaoAutenticado):
    """E-mail ou senha incorretos (ou conta inativa)."""


class ServicoAutenticacao:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def registrar(self, dados: RegistroEntrada) -> Usuario:
        # O cadastro público nunca cria admin.
        return ServicoUsuarios(self._sessao).criar(
            dados.nome, dados.email, dados.senha, Papel.CLIENTE
        )

    def autenticar(self, email: str, senha: str) -> Usuario:
        """Mesma mensagem e tempo parecido para e-mail inexistente, senha errada ou inativo."""
        try:
            normalizado: str | None = normalizar_email(email)
        except ValueError:
            normalizado = None  # segue para o hash fictício e o 401 genérico
        usuario = (
            self._sessao.scalars(select(Usuario).where(Usuario.email == normalizado)).one_or_none()
            if normalizado
            else None
        )
        senha_ok = verificar_senha(senha, usuario.senha_hash if usuario else None)
        if usuario is None or not senha_ok or not usuario.ativo:
            raise CredenciaisInvalidas(MENSAGEM_LOGIN_INVALIDO)
        if precisa_rehash(usuario.senha_hash):
            usuario.senha_hash = gerar_hash(senha)
            self._sessao.commit()
        return usuario
