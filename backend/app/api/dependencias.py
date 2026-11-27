"""Dependências comuns das rotas: sessão, configuração, usuário autenticado e papéis."""

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.banco import obter_sessao
from app.core.config import Configuracoes, obter_configuracoes
from app.core.erros import AcessoNegado, NaoAutenticado, NaoEncontrado, TokenRecusado
from app.core.seguranca import TokenInvalido, ler_token_acesso
from app.modelos import Papel, Usuario

# auto_error=False: sem token, devolvemos nosso próprio 401 em português.
_esquema_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

SessaoDep = Annotated[Session, Depends(obter_sessao)]
ConfigDep = Annotated[Configuracoes, Depends(obter_configuracoes)]


def usuario_atual(
    sessao: SessaoDep,
    config: ConfigDep,
    token: Annotated[str | None, Depends(_esquema_oauth2)],
) -> Usuario:
    if not token:
        raise NaoAutenticado("Entre na sua conta para continuar.")
    try:
        dados = ler_token_acesso(token, config)
    except TokenInvalido as erro:
        raise TokenRecusado("Sua sessão expirou ou é inválida. Entre novamente.") from erro
    usuario = sessao.get(Usuario, dados.usuario_id)
    # O papel é lido do banco (não do token): rebaixar ou desativar vale na hora.
    if usuario is None or not usuario.ativo:
        raise TokenRecusado("Sua sessão expirou ou é inválida. Entre novamente.")
    # Troca de senha ou de e-mail sobe a versão e derruba as sessões abertas antes dela.
    if dados.versao != usuario.versao_credenciais:
        raise TokenRecusado("Sua senha ou seu e-mail foi alterado. Entre novamente.")
    return usuario


UsuarioDep = Annotated[Usuario, Depends(usuario_atual)]


def exigir_admin(usuario: UsuarioDep) -> Usuario:
    if usuario.papel is not Papel.ADMIN:
        raise AcessoNegado("Você não tem permissão para acessar esta área.")
    return usuario


AdminDep = Annotated[Usuario, Depends(exigir_admin)]


def garantir_acesso(usuario: Usuario, dono_id: uuid.UUID | None, recurso: str) -> None:
    """Cliente só acessa o que é seu; admin acessa tudo.

    Para quem não é dono, responde 404 (e não 403) para não revelar que o recurso existe.
    """
    if usuario.papel is Papel.ADMIN or (dono_id is not None and dono_id == usuario.id):
        return
    raise NaoEncontrado(f"{recurso} não encontrado(a).")
