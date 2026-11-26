"""Erros no formato RFC 7807 (`application/problem+json`), com mensagens em português."""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, ClassVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

TIPO_PROBLEMA = "application/problem+json"


class ErroDominio(Exception):
    """Erro de regra de negócio, convertido em resposta HTTP pelo tratador."""

    status = HTTPStatus.BAD_REQUEST
    cabecalhos: ClassVar[Mapping[str, str] | None] = None

    def __init__(self, detalhe: str) -> None:
        super().__init__(detalhe)
        self.detalhe = detalhe

    def cabecalhos_resposta(self) -> Mapping[str, str] | None:
        return self.cabecalhos


class NaoEncontrado(ErroDominio):
    status = HTTPStatus.NOT_FOUND


class Conflito(ErroDominio):
    status = HTTPStatus.CONFLICT


class AcessoNegado(ErroDominio):
    status = HTTPStatus.FORBIDDEN


class NaoAutenticado(ErroDominio):
    status = HTTPStatus.UNAUTHORIZED
    cabecalhos: ClassVar[Mapping[str, str] | None] = {"WWW-Authenticate": "Bearer"}


class TokenRecusado(NaoAutenticado):
    """Token presente, mas inválido ou expirado (RFC 6750, seção 3)."""

    cabecalhos: ClassVar[Mapping[str, str] | None] = {
        "WWW-Authenticate": 'Bearer error="invalid_token"'
    }


class DadosRecusados(ErroDominio):
    status = HTTPStatus.UNPROCESSABLE_ENTITY


def problema(
    request: Request,
    status: int,
    detalhe: str,
    headers: Mapping[str, str] | None = None,
    **extras: Any,
) -> JSONResponse:
    corpo = {
        "type": "about:blank",
        "title": HTTPStatus(status).phrase,
        "status": status,
        "detail": detalhe,
        "instance": request.url.path,
        **extras,
    }
    return JSONResponse(corpo, status_code=status, media_type=TIPO_PROBLEMA, headers=headers)


def _campo(loc: tuple[Any, ...]) -> str:
    return ".".join(str(parte) for parte in loc if parte not in {"body", "query", "path"})


async def _tratar_validacao(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):  # pragma: no cover
        raise exc
    erros = [{"campo": _campo(e["loc"]), "mensagem": e["msg"]} for e in exc.errors()]
    return problema(request, 422, "Dados inválidos.", erros=erros)


async def _tratar_http(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):  # pragma: no cover
        raise exc
    # Preserva cabeçalhos como WWW-Authenticate (401) e Allow (405).
    headers = getattr(exc, "headers", None)
    if isinstance(exc.detail, str):
        return problema(request, exc.status_code, exc.detail, headers=headers)
    return problema(
        request,
        exc.status_code,
        HTTPStatus(exc.status_code).phrase,
        headers=headers,
        dados=exc.detail,
    )


async def _tratar_dominio(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ErroDominio):  # pragma: no cover
        raise exc
    return problema(request, exc.status, exc.detalhe, headers=exc.cabecalhos_resposta())


def registrar_tratadores(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _tratar_validacao)
    app.add_exception_handler(StarletteHTTPException, _tratar_http)
    app.add_exception_handler(ErroDominio, _tratar_dominio)
