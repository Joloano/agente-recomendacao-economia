"""Estratégias por recurso (padrões Strategy e Template Method) e o registro que as cria.

`EstrategiaRecurso.recomendar` fixa o ciclo do agente (filtrar → pontuar → ordenar);
cada recurso só define o que varia: qual recurso atende e qual ação sugerir.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from decimal import Decimal
from types import MappingProxyType
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
    """Registro imutável (Simple Factory / Registry) que cria a estratégia de cada recurso.

    É uma instância entregue por injeção de dependência, não um estado global: cada agente
    (ou teste) usa a fábrica que receber. Para um novo recurso, crie outra fábrica com
    `com(...)`, sem alterar a original.
    """

    def __init__(self, estrategias: Iterable[type[EstrategiaRecurso]]) -> None:
        registro: dict[Recurso, type[EstrategiaRecurso]] = {}
        for estrategia in estrategias:
            if estrategia.recurso in registro:
                raise ErroAgente(f"Estratégia duplicada para {estrategia.recurso}.")
            registro[estrategia.recurso] = estrategia
        self._registro: Mapping[Recurso, type[EstrategiaRecurso]] = MappingProxyType(registro)

    @property
    def recursos(self) -> frozenset[Recurso]:
        return frozenset(self._registro)

    def com(self, *estrategias: type[EstrategiaRecurso]) -> "FabricaEstrategia":
        return FabricaEstrategia([*self._registro.values(), *estrategias])

    def para(
        self, recurso: Recurso, calculadora: CalculadoraUtilidade | None = None
    ) -> EstrategiaRecurso:
        try:
            estrategia = self._registro[recurso]
        except KeyError:
            raise ErroAgente(f"Recurso ainda não suportado: {recurso}.") from None
        return estrategia(calculadora=calculadora)


FABRICA_PADRAO = FabricaEstrategia([EstrategiaEnergia])
