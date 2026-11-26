"""Erros no formato RFC 7807 (`application/problem+json`), com mensagens em português."""

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

TIPO_PROBLEMA = "application/problem+json"


class ErroDominio(Exception):
    """Erro de regra de negócio, convertido em resposta HTTP pelo tratador."""

    status = HTTPStatus.BAD_REQUEST

    def __init__(self, detalhe: str) -> None:
        super().__init__(detalhe)
        self.detalhe = detalhe


class NaoEncontrado(ErroDominio):
    status = HTTPStatus.NOT_FOUND


class Conflito(ErroDominio):
    status = HTTPStatus.CONFLICT


class AcessoNegado(ErroDominio):
    status = HTTPStatus.FORBIDDEN


def problema(request: Request, status: int, detalhe: str, **extras: Any) -> JSONResponse:
    corpo = {
        "type": "about:blank",
        "title": HTTPStatus(status).phrase,
        "status": status,
        "detail": detalhe,
        "instance": request.url.path,
        **extras,
    }
    return JSONResponse(corpo, status_code=status, media_type=TIPO_PROBLEMA)


def _campo(loc: tuple[Any, ...]) -> str:
    return ".".join(str(parte) for parte in loc if parte not in {"body", "query", "path"})


async def _tratar_validacao(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(
        exc, RequestValidationError
    ):  # pragma: no cover - registrado só para RequestValidationError
        raise exc
    erros = [{"campo": _campo(e["loc"]), "mensagem": e["msg"]} for e in exc.errors()]
    return problema(request, 422, "Dados inválidos.", erros=erros)


async def _tratar_http(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(
        exc, StarletteHTTPException
    ):  # pragma: no cover - registrado só para StarletteHTTPException
        raise exc
    return problema(request, exc.status_code, str(exc.detail))


async def _tratar_dominio(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ErroDominio):  # pragma: no cover - registrado só para ErroDominio
        raise exc
    return problema(request, exc.status, exc.detalhe)


def registrar_tratadores(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _tratar_validacao)
    app.add_exception_handler(StarletteHTTPException, _tratar_http)
    app.add_exception_handler(ErroDominio, _tratar_dominio)
