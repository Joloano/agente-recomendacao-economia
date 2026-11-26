"""Casos de uso de conta: cadastro e login."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.erros import Conflito, DadosRecusados, NaoAutenticado
from app.core.seguranca import (
    SenhaFraca,
    gerar_hash,
    precisa_rehash,
    validar_politica_senha,
    verificar_senha,
)
from app.esquemas.autenticacao import RegistroEntrada
from app.modelos import Papel, Usuario

MENSAGEM_LOGIN_INVALIDO = "E-mail ou senha incorretos."


class SenhaRecusada(DadosRecusados):
    """Senha fora da política mínima."""


class CredenciaisInvalidas(NaoAutenticado):
    """E-mail ou senha incorretos (ou conta inativa)."""


class ServicoAutenticacao:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def registrar(self, dados: RegistroEntrada) -> Usuario:
        try:
            validar_politica_senha(dados.senha, dados.email)
        except SenhaFraca as erro:
            raise SenhaRecusada(str(erro)) from erro
        usuario = Usuario(
            nome=dados.nome,
            email=dados.email,
            senha_hash=gerar_hash(dados.senha),
            papel=Papel.CLIENTE,  # o cadastro público nunca cria admin
        )
        self._sessao.add(usuario)
        try:
            self._sessao.commit()
        except IntegrityError as erro:
            self._sessao.rollback()
            raise Conflito("Este e-mail já está cadastrado. Quer entrar?") from erro
        self._sessao.refresh(usuario)
        return usuario

    def autenticar(self, email: str, senha: str) -> Usuario:
        """Mesma mensagem e tempo parecido para e-mail inexistente, senha errada ou inativo."""
        usuario = self._sessao.scalars(
            select(Usuario).where(Usuario.email == email.strip().lower())
        ).one_or_none()
        senha_ok = verificar_senha(senha, usuario.senha_hash if usuario else None)
        if usuario is None or not senha_ok or not usuario.ativo:
            raise CredenciaisInvalidas(MENSAGEM_LOGIN_INVALIDO)
        if precisa_rehash(usuario.senha_hash):
            usuario.senha_hash = gerar_hash(senha)
            self._sessao.commit()
        return usuario
