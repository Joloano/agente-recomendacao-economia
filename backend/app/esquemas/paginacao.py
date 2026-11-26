"""Paginação padrão de todas as listas da API (#87)."""

from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")

TAMANHO_PADRAO = 20
TAMANHO_MAXIMO = 100


class ParametrosPagina(BaseModel):
    pagina: int
    tamanho: int

    @property
    def deslocamento(self) -> int:
        return (self.pagina - 1) * self.tamanho


def parametros_pagina(
    pagina: Annotated[int, Query(ge=1, description="Página, começando em 1")] = 1,
    tamanho: Annotated[
        int, Query(ge=1, le=TAMANHO_MAXIMO, description="Itens por página")
    ] = TAMANHO_PADRAO,
) -> ParametrosPagina:
    return ParametrosPagina(pagina=pagina, tamanho=tamanho)


class Pagina(BaseModel, Generic[T]):
    itens: list[T]
    total: int
    pagina: int
    tamanho: int

    @property
    def paginas(self) -> int:
        return max(1, -(-self.total // self.tamanho))
