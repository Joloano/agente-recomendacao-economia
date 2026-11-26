"""Estratégias por recurso (padrões Strategy, Template Method e Factory Method).

`EstrategiaRecurso.recomendar` fixa o ciclo do agente (filtrar → pontuar → ordenar);
cada recurso só define o que varia: qual recurso atende e qual ação sugerir.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from decimal import Decimal
from typing import ClassVar

from app.agente.calculadora import CalculadoraUtilidade
from app.agente.dominio import ErroAgente, Oportunidade, Pesos, Recomendacao, Recurso
from app.agente.regras import RegraElegibilidade, montar_cadeia_padrao


class EstrategiaRecurso(ABC):
    recurso: ClassVar[Recurso]

    def __init__(
        self,
        regras: RegraElegibilidade | None = None,
        calculadora: CalculadoraUtilidade | None = None,
    ) -> None:
        self._regras = regras or montar_cadeia_padrao()
        self._calculadora = calculadora or CalculadoraUtilidade()

    # --- Template Method ---
    def recomendar(
        self,
        oportunidades: Iterable[Oportunidade],
        pesos: Pesos,
        pendentes: set[str] | None = None,
    ) -> list[Recomendacao]:
        elegiveis = self.elegiveis(oportunidades)
        # A régua da nota de economia usa todos os elegíveis, para a nota não mudar
        # quando o usuário responde a uma recomendação.
        maior_economia = max((o.economia_potencial for o in elegiveis), default=Decimal(0))
        candidatas = [o for o in elegiveis if pendentes is None or o.id in pendentes]
        recomendacoes = [self._pontuar(o, maior_economia, pesos) for o in candidatas]
        return self._calculadora.ordenar(recomendacoes)

    def elegiveis(self, oportunidades: Iterable[Oportunidade]) -> list[Oportunidade]:
        return [o for o in self._do_recurso(oportunidades) if self.motivo_inelegivel(o) is None]

    def motivo_inelegivel(self, oportunidade: Oportunidade) -> str | None:
        return self._regras.avaliar(oportunidade)

    def _do_recurso(self, oportunidades: Iterable[Oportunidade]) -> list[Oportunidade]:
        return [o for o in oportunidades if o.recurso is self.recurso]

    def _pontuar(
        self, oportunidade: Oportunidade, maior_economia: Decimal, pesos: Pesos
    ) -> Recomendacao:
        notas = self._calculadora.notas(oportunidade, maior_economia)
        contribuicoes = self._calculadora.contribuicoes(notas, pesos)
        return Recomendacao(
            oportunidade=oportunidade,
            notas=notas,
            utilidade=self._calculadora.utilidade(contribuicoes),
            contribuicoes=contribuicoes,
            acao=self.descricao_acao(oportunidade),
        )

    # --- Passo que varia por recurso ---
    @abstractmethod
    def descricao_acao(self, oportunidade: Oportunidade) -> str: ...


class EstrategiaEnergia(EstrategiaRecurso):
    recurso = Recurso.ENERGIA
    ACOES: ClassVar[dict[str, str]] = {
        "lavanderia": "Acumular roupas e fazer lavagens com carga completa.",
        "entretenimento": (
            "Desligar a TV quando ninguém estiver assistindo, sem deixá-la como som de fundo."
        ),
        "trabalho_estudo": (
            "Ativar o modo de economia de energia e desligar o computador ao fim do uso."
        ),
        "iluminacao": "Apagar as luzes de ambientes vazios e aproveitar a luz natural.",
        "cozinha": "Planejar o uso do forno e assar mais de um alimento por vez.",
        "climatizacao": "Ligar o ventilador só com pessoas no ambiente e desligá-lo ao sair.",
    }
    ACAO_PADRAO = "Reduzir o tempo de uso do equipamento."

    def descricao_acao(self, oportunidade: Oportunidade) -> str:
        return self.ACOES.get(oportunidade.categoria, self.ACAO_PADRAO)


class FabricaEstrategia:
    """Factory Method: novos recursos são registrados aqui, sem mudar quem os usa."""

    _registro: ClassVar[dict[Recurso, type[EstrategiaRecurso]]] = {
        Recurso.ENERGIA: EstrategiaEnergia,
    }

    @classmethod
    def registrar(cls, estrategia: type[EstrategiaRecurso]) -> None:
        cls._registro[estrategia.recurso] = estrategia

    @classmethod
    def para(cls, recurso: Recurso) -> EstrategiaRecurso:
        try:
            return cls._registro[recurso]()
        except KeyError:
            raise ErroAgente(f"Recurso ainda não suportado: {recurso}.") from None
