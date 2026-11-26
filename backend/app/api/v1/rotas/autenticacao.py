from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencias import ConfigDep, SessaoDep, UsuarioDep
from app.core.seguranca import criar_token_acesso
from app.esquemas.autenticacao import RegistroEntrada, Token, UsuarioSaida
from app.servicos.autenticacao import ServicoAutenticacao

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/registrar",
    response_model=UsuarioSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma conta de cliente",
    responses={
        409: {"description": "E-mail já cadastrado"},
        422: {"description": "Dados inválidos"},
    },
)
def registrar(dados: RegistroEntrada, sessao: SessaoDep) -> UsuarioSaida:
    usuario = ServicoAutenticacao(sessao).registrar(dados)
    return UsuarioSaida.model_validate(usuario)


@router.post(
    "/login",
    response_model=Token,
    summary="Entra com e-mail e senha (OAuth2 password) e recebe um token de acesso",
    responses={401: {"description": "E-mail ou senha incorretos"}},
)
def entrar(
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    sessao: SessaoDep,
    config: ConfigDep,
) -> Token:
    # No OAuth2, o campo se chama "username"; aqui ele recebe o e-mail.
    usuario = ServicoAutenticacao(sessao).autenticar(formulario.username, formulario.password)
    token, expira = criar_token_acesso(usuario.id, usuario.papel, config)
    return Token(access_token=token, expira_em=expira)


@router.get("/eu", response_model=UsuarioSaida, summary="Dados do usuário autenticado")
def eu(usuario: UsuarioDep) -> UsuarioSaida:
    return UsuarioSaida.model_validate(usuario)
