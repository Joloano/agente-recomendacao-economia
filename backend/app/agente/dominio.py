"""Objetos de domínio do agente: puros, imutáveis e sem dependência de banco ou HTTP."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

TOLERANCIA_SOMA_PESOS = Decimal("0.001")
ESCALA_MINIMA, ESCALA_MAXIMA = 1, 5


class Recurso(StrEnum):
    ENERGIA = "energia"
    AGUA = "agua"

    @property
    def unidade(self) -> str:
        return "kWh" if self is Recurso.ENERGIA else "L"


class Essencialidade(StrEnum):
    ESSENCIAL = "essencial"
    IMPORTANTE = "importante"
    NAO_ESSENCIAL = "nao_essencial"


class Criterio(StrEnum):
    ECONOMIA = "economia"
    CONFORTO = "conforto"
    FLEXIBILIDADE = "flexibilidade"
    BAIXO_ESFORCO = "baixo_esforco"


class ErroAgente(Exception):
    """Violação de regra do agente."""


@dataclass(frozen=True, slots=True)
class Pesos:
    """Prioridades dos moradores; somam 1."""

    economia: Decimal
    conforto: Decimal
    flexibilidade: Decimal
    baixo_esforco: Decimal

    def __post_init__(self) -> None:
        valores = self.como_dict().values()
        if any(not Decimal(0) <= valor <= Decimal(1) for valor in valores):
            raise ErroAgente("Cada peso deve estar entre 0 e 1.")
        if abs(sum(valores, Decimal(0)) - 1) > TOLERANCIA_SOMA_PESOS:
            raise ErroAgente("Os pesos devem somar 1.")

    def como_dict(self) -> dict[Criterio, Decimal]:
        return {
            Criterio.ECONOMIA: self.economia,
            Criterio.CONFORTO: self.conforto,
            Criterio.FLEXIBILIDADE: self.flexibilidade,
            Criterio.BAIXO_ESFORCO: self.baixo_esforco,
        }


def _validar_escala(nome: str, valor: int) -> None:
    if not ESCALA_MINIMA <= valor <= ESCALA_MAXIMA:
        raise ErroAgente(f"{nome} deve estar entre {ESCALA_MINIMA} e {ESCALA_MAXIMA}.")


@dataclass(frozen=True, slots=True)
class Oportunidade:
    """Um equipamento visto como possível oportunidade de economia."""

    id: str
    nome: str
    categoria: str
    recurso: Recurso
    consumo_diario: Decimal
    reducao_uso: bool
    essencialidade: Essencialidade
    impacto_conforto: int
    flexibilidade: int
    esforco: int
    economia_potencial: Decimal
    ordem: int = 0

    def __post_init__(self) -> None:
        _validar_escala("impacto_conforto", self.impacto_conforto)
        _validar_escala("flexibilidade", self.flexibilidade)
        _validar_escala("esforco", self.esforco)
        if self.consumo_diario < 0 or self.economia_potencial < 0:
            raise ErroAgente("Consumo e economia não podem ser negativos.")


@dataclass(frozen=True, slots=True)
class Notas:
    economia: Decimal
    conforto: Decimal
    flexibilidade: Decimal
    baixo_esforco: Decimal

    def como_dict(self) -> dict[Criterio, Decimal]:
        return {
            Criterio.ECONOMIA: self.economia,
            Criterio.CONFORTO: self.conforto,
            Criterio.FLEXIBILIDADE: self.flexibilidade,
            Criterio.BAIXO_ESFORCO: self.baixo_esforco,
        }


@dataclass(frozen=True, slots=True)
class Recomendacao:
    oportunidade: Oportunidade
    notas: Notas
    utilidade: Decimal
    contribuicoes: dict[Criterio, Decimal]
    acao: str

    @property
    def recurso(self) -> Recurso:
        return self.oportunidade.recurso
