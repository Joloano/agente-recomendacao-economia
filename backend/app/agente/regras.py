"""Regras de elegibilidade encadeadas (padrão Chain of Responsibility).

Cada regra decide sobre um único critério. A primeira que reprovar interrompe a
cadeia e devolve o motivo, que alimenta a explicação ao usuário.
"""

from abc import ABC, abstractmethod

from app.agente.dominio import Essencialidade, Oportunidade

IMPACTO_CONFORTO_MAXIMO = 3


class RegraElegibilidade(ABC):
    def __init__(self) -> None:
        self._proxima: RegraElegibilidade | None = None

    def encadear(self, proxima: "RegraElegibilidade") -> "RegraElegibilidade":
        self._proxima = proxima
        return proxima

    def avaliar(self, oportunidade: Oportunidade) -> str | None:
        """Devolve o motivo da reprovação, ou None se todas as regras aprovarem."""
        motivo = self._reprovar(oportunidade)
        if motivo is not None or self._proxima is None:
            return motivo
        return self._proxima.avaliar(oportunidade)

    @abstractmethod
    def _reprovar(self, oportunidade: Oportunidade) -> str | None: ...


class RegraReducaoUso(RegraElegibilidade):
    def _reprovar(self, oportunidade: Oportunidade) -> str | None:
        return None if oportunidade.reducao_uso else "o uso não pode ser reduzido"


class RegraEconomiaPositiva(RegraElegibilidade):
    def _reprovar(self, oportunidade: Oportunidade) -> str | None:
        return None if oportunidade.economia_potencial > 0 else "não há economia possível"


class RegraNaoEssencial(RegraElegibilidade):
    def _reprovar(self, oportunidade: Oportunidade) -> str | None:
        if oportunidade.essencialidade is Essencialidade.ESSENCIAL:
            return "é um equipamento essencial"
        return None


class RegraConfortoMaximo(RegraElegibilidade):
    def _reprovar(self, oportunidade: Oportunidade) -> str | None:
        if oportunidade.impacto_conforto > IMPACTO_CONFORTO_MAXIMO:
            return "o impacto no conforto seria alto demais"
        return None


def montar_cadeia_padrao() -> RegraElegibilidade:
    inicio = RegraReducaoUso()
    (
        inicio.encadear(RegraEconomiaPositiva())
        .encadear(RegraNaoEssencial())
        .encadear(RegraConfortoMaximo())
    )
    return inicio
