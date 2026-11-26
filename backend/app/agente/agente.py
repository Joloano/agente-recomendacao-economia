"""Fachada do agente (padrão Facade): a única porta de entrada para a API e a voz."""

from collections import Counter
from collections.abc import Sequence
from decimal import Decimal

from app.agente.calculadora import CalculadoraUtilidade
from app.agente.dominio import ErroAgente, Oportunidade, Pesos, Recomendacao, Recurso
from app.agente.estrategias import FABRICA_PADRAO, EstrategiaRecurso, FabricaEstrategia
from app.agente.simulacao import EstadoSimulacao, RegistroFeedback, Resposta


class AgenteRecomendador:
    def __init__(
        self,
        recursos: Sequence[Recurso] = (Recurso.ENERGIA,),
        fabrica: FabricaEstrategia = FABRICA_PADRAO,
        calculadora: CalculadoraUtilidade | None = None,
    ) -> None:
        if not recursos:
            raise ErroAgente("Informe ao menos um recurso.")
        if len(set(recursos)) != len(recursos):
            raise ErroAgente("Recursos repetidos.")
        self._calculadora = calculadora or CalculadoraUtilidade()
        # A mesma calculadora é usada pelas estratégias e pela ordenação final.
        self._estrategias: dict[Recurso, EstrategiaRecurso] = {
            r: fabrica.para(r, calculadora=self._calculadora) for r in recursos
        }

    @property
    def recursos(self) -> list[Recurso]:
        return list(self._estrategias)

    def perceber(self, oportunidades: Sequence[Oportunidade]) -> EstadoSimulacao:
        """Cria o estado inicial com o consumo atual e as oportunidades elegíveis pendentes."""
        repetidos = [id_ for id_, n in Counter(o.id for o in oportunidades).items() if n > 1]
        if repetidos:
            raise ErroAgente(f"Identificadores repetidos: {', '.join(sorted(repetidos))}.")
        consumo = {
            recurso: sum(
                (o.consumo_diario for o in oportunidades if o.recurso is recurso), Decimal(0)
            )
            for recurso in self.recursos
        }
        pendentes = {o.id for e in self._estrategias.values() for o in e.elegiveis(oportunidades)}
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
            for e in self._estrategias.values()
            for r in e.recomendar(oportunidades, pesos, pendentes=estado.pendentes)
        ]
        return self._calculadora.ordenar(recomendacoes)

    def responder(
        self, estado: EstadoSimulacao, oportunidade: Oportunidade, resposta: Resposta
    ) -> RegistroFeedback:
        return estado.registrar(oportunidade, resposta)

    def explicar_inelegibilidade(self, oportunidade: Oportunidade) -> str | None:
        """Motivo pelo qual a oportunidade não é recomendada, usando as regras deste agente."""
        estrategia = self._estrategias.get(oportunidade.recurso)
        if estrategia is None:
            raise ErroAgente(f"Este agente não trata o recurso {oportunidade.recurso}.")
        return estrategia.motivo_inelegivel(oportunidade)
