from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencias import ConfigDep, SessaoDep, UsuarioDep
from app.core.seguranca import criar_token_acesso
from app.esquemas.autenticacao import RegistroEntrada, Token, UsuarioSaida
from app.servicos.autenticacao import ServicoAutenticacao
from app.servicos.limite import LimitadorTentativas

RESPOSTA_429: dict[int | str, dict[str, Any]] = {
    429: {"description": "Muitas tentativas; veja o cabeçalho Retry-After"},
    503: {"description": "Servidor ocupado; veja o cabeçalho Retry-After"},
}


def _ip(request: Request) -> str:
    # Com --proxy-headers, o Uvicorn já põe aqui o IP real vindo do proxy confiável.
    return request.client.host if request.client else "desconhecido"


router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/registrar",
    response_model=UsuarioSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma conta de cliente",
    responses={
        409: {"description": "E-mail já cadastrado"},
        **RESPOSTA_429,
        422: {"description": "Dados inválidos"},
    },
)
def registrar(
    dados: RegistroEntrada, sessao: SessaoDep, config: ConfigDep, request: Request
) -> UsuarioSaida:
    # Toda tentativa de cadastro conta, com sucesso ou não.
    LimitadorTentativas(sessao, config).reservar("cadastro", ip=_ip(request))
    usuario = ServicoAutenticacao(sessao).registrar(dados)
    return UsuarioSaida.model_validate(usuario)


@router.post(
    "/login",
    response_model=Token,
    summary="Entra com e-mail e senha (OAuth2 password) e recebe um token de acesso",
    responses={401: {"description": "E-mail ou senha incorretos"}, **RESPOSTA_429},
)
def entrar(
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    sessao: SessaoDep,
    config: ConfigDep,
    request: Request,
) -> Token:
    # No OAuth2, o campo se chama "username"; aqui ele recebe o e-mail.
    limitador = LimitadorTentativas(sessao, config)
    # Reserva antes do argon2: quem estourou o limite não gasta CPU nem memória, e uma
    # rajada simultânea não passa (a tentativa já conta antes da verificação da senha).
    ip = _ip(request)
    reserva = limitador.reservar("login", email=formulario.username, ip=ip)
    usuario = ServicoAutenticacao(sessao).autenticar(formulario.username, formulario.password)
    limitador.liberar(reserva, formulario.username, ip)
    token, expira = criar_token_acesso(usuario.id, usuario.papel, config)
    return Token(access_token=token, expira_em=expira)


@router.get("/eu", response_model=UsuarioSaida, summary="Dados do usuário autenticado")
def eu(usuario: UsuarioDep) -> UsuarioSaida:
    return UsuarioSaida.model_validate(usuario)
