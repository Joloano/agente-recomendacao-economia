"""Fachada do agente (padrão Facade): a única porta de entrada para a API e a voz."""

from collections.abc import Sequence
from decimal import Decimal

from app.agente.calculadora import CalculadoraUtilidade
from app.agente.dominio import ErroAgente, Oportunidade, Pesos, Recomendacao, Recurso
from app.agente.estrategias import EstrategiaRecurso, FabricaEstrategia
from app.agente.simulacao import EstadoSimulacao, RegistroFeedback, Resposta


class AgenteRecomendador:
    def __init__(
        self,
        recursos: Sequence[Recurso] = (Recurso.ENERGIA,),
        calculadora: CalculadoraUtilidade | None = None,
    ) -> None:
        if not recursos:
            raise ErroAgente("Informe ao menos um recurso.")
        self._estrategias: list[EstrategiaRecurso] = [FabricaEstrategia.para(r) for r in recursos]
        self._calculadora = calculadora or CalculadoraUtilidade()

    @property
    def recursos(self) -> list[Recurso]:
        return [e.recurso for e in self._estrategias]

    def perceber(self, oportunidades: Sequence[Oportunidade]) -> EstadoSimulacao:
        """Cria o estado inicial com o consumo atual e as oportunidades elegíveis pendentes."""
        consumo = {
            recurso: sum(
                (o.consumo_diario for o in oportunidades if o.recurso is recurso), Decimal(0)
            )
            for recurso in self.recursos
        }
        pendentes = {o.id for e in self._estrategias for o in e.elegiveis(oportunidades)}
        return EstadoSimulacao(
            consumo_inicial=dict(consumo), consumo_estimado=dict(consumo), pendentes=pendentes
        )

    def recomendar(
        self, oportunidades: Sequence[Oportunidade], pesos: Pesos, estado: EstadoSimulacao
    ) -> list[Recomendacao]:
        """Recomendações pendentes, ordenadas; com vários recursos, numa lista única.

        A nota de economia é normalizada dentro de cada recurso (kWh não se compara com litros).
        """
        recomendacoes = [
            r
            for e in self._estrategias
            for r in e.recomendar(oportunidades, pesos, pendentes=estado.pendentes)
        ]
        return self._calculadora.ordenar(recomendacoes)

    def responder(
        self, estado: EstadoSimulacao, oportunidade: Oportunidade, resposta: Resposta
    ) -> RegistroFeedback:
        return estado.registrar(oportunidade, resposta)

    def explicar_inelegibilidade(self, oportunidade: Oportunidade) -> str | None:
        estrategia = FabricaEstrategia.para(oportunidade.recurso)
        return estrategia.motivo_inelegivel(oportunidade)
