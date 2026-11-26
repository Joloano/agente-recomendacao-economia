"""Regressão: o novo núcleo reproduz o agente original (legado/agente_energia.py) em R01–R10.

A elegibilidade, a ordem, as utilidades, o consumo após cada resposta e o histórico são
calculados de forma independente nos dois agentes e comparados passo a passo.

Sobre arredondamento: o legado arredonda o consumo para 3 casas a cada passo; o núcleo novo
usa Decimal sem arredondar. Como todas as quantidades do dataset têm no máximo 3 casas, os
resultados coincidem exatamente, e por isso a comparação de consumo é por igualdade.
"""

import importlib.util
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.agente import AgenteRecomendador, Essencialidade, Oportunidade, Pesos, Recurso, Resposta

RAIZ = Path(__file__).resolve().parents[3]
TOLERANCIA_UTILIDADE = Decimal("0.000001")


def _carregar_legado() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "legado_agente", RAIZ / "legado" / "agente_energia.py"
    )
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


legado = _carregar_legado()
REGISTROS: list[dict[str, Any]] = legado.carregar_dataset(legado.CAMINHO_DATASET)
RESIDENCIAS = sorted({r["residencia_id"] for r in REGISTROS})


def _d(valor: float) -> Decimal:
    return Decimal(str(valor))


def _converter(registros: list[dict[str, Any]]) -> tuple[list[Oportunidade], Pesos]:
    primeiro = registros[0]
    pesos = Pesos(
        _d(primeiro["peso_economia"]),
        _d(primeiro["peso_conforto"]),
        _d(primeiro["peso_flexibilidade"]),
        _d(primeiro["peso_baixo_esforco"]),
    )
    oportunidades = [
        Oportunidade(
            id=r["equipamento_id"],
            nome=r["equipamento"],
            categoria=r["categoria"],
            recurso=Recurso.ENERGIA,
            consumo_diario=_d(r["consumo_diario_estimado_kwh"]),
            reducao_uso=r["reducao_uso"],
            essencialidade=Essencialidade(r["essencialidade"]),
            impacto_conforto=r["impacto_conforto_1a5"],
            flexibilidade=r["flexibilidade_reducao_uso_1a5"],
            esforco=r["esforco_1a5"],
            economia_potencial=_d(r["economia_potencial_reducao_kwh"]),
            ordem=posicao,
        )
        for posicao, r in enumerate(registros)
    ]
    return oportunidades, pesos


class Simulacoes:
    """Os dois agentes, lado a lado, para a mesma residência."""

    def __init__(self, residencia: str) -> None:
        registros = legado.selecionar_residencia(REGISTROS, residencia)
        self.oportunidades, self.pesos = _converter(registros)
        self.agente = AgenteRecomendador()
        self.estado = self.agente.perceber(self.oportunidades)

        self.percepcao_legado = legado.perceber(registros)
        self.estado_legado = legado.criar_estado(self.percepcao_legado)
        for equipamento in legado.identificar_elegiveis(self.percepcao_legado["equipamentos"]):
            self.estado_legado["pendentes"].append(equipamento["equipamento_id"])

    def ranking_novo(self) -> list[tuple[str, Decimal]]:
        recs = self.agente.recomendar(self.oportunidades, self.pesos, self.estado)
        return [(r.oportunidade.id, r.utilidade) for r in recs]

    def ranking_legado(self) -> list[tuple[str, float]]:
        recs = legado.ordenar_recomendacoes(
            legado.gerar_recomendacoes(self.estado_legado, self.percepcao_legado)
        )
        return [(r["oportunidade"]["equipamento_id"], r["utilidade"]) for r in recs]

    def responder(self, id_: str, resposta: Resposta) -> None:
        oportunidade = next(o for o in self.oportunidades if o.id == id_)
        self.agente.responder(self.estado, oportunidade, resposta)
        equipamento = next(
            e for e in self.percepcao_legado["equipamentos"] if e["equipamento_id"] == id_
        )
        legado.registrar_feedback(self.estado_legado, equipamento, resposta.value)

    def conferir(self) -> None:
        novo, original = self.ranking_novo(), self.ranking_legado()
        assert [i for i, _ in novo] == [i for i, _ in original]
        for (_, utilidade), (_, utilidade_legado) in zip(novo, original, strict=True):
            assert abs(utilidade - _d(utilidade_legado)) < TOLERANCIA_UTILIDADE
        consumo = self.estado.consumo_estimado[Recurso.ENERGIA]
        assert consumo == _d(self.estado_legado["consumo_estimado_kwh"])
        assert self.estado.aceitas == self.estado_legado["aceitas"]
        assert self.estado.rejeitadas == self.estado_legado["rejeitadas"]


@pytest.mark.parametrize("residencia", RESIDENCIAS)
def test_mesmos_elegiveis_e_consumo_inicial(residencia: str) -> None:
    sim = Simulacoes(residencia)

    assert sim.estado.pendentes == set(sim.estado_legado["pendentes"])
    assert sim.estado.consumo_inicial[Recurso.ENERGIA] == _d(
        sim.estado_legado["consumo_inicial_kwh"]
    )


Escolha = Callable[[int], Resposta]
ESTRATEGIAS_DE_RESPOSTA: dict[str, Escolha] = {
    "aceita_tudo": lambda _: Resposta.ACEITAR,
    "rejeita_tudo": lambda _: Resposta.REJEITAR,
    "alterna": lambda passo: Resposta.ACEITAR if passo % 2 == 0 else Resposta.REJEITAR,
}


@pytest.mark.parametrize("residencia", RESIDENCIAS)
@pytest.mark.parametrize("estrategia", ESTRATEGIAS_DE_RESPOSTA)
def test_mesma_ordem_utilidade_e_consumo_a_cada_resposta(residencia: str, estrategia: str) -> None:
    """Responde sempre à primeira recomendação da lista, como um usuário apressado."""
    sim = Simulacoes(residencia)
    escolher = ESTRATEGIAS_DE_RESPOSTA[estrategia]

    sim.conferir()
    passo = 0
    while sim.estado.pendentes:
        primeira, _ = sim.ranking_novo()[0]
        sim.responder(primeira, escolher(passo))
        sim.conferir()
        passo += 1

    assert passo == len(sim.estado.historico) > 0


@pytest.mark.parametrize("residencia", RESIDENCIAS)
def test_responder_pela_ultima_da_lista_tambem_coincide(residencia: str) -> None:
    sim = Simulacoes(residencia)

    while sim.estado.pendentes:
        ultima, _ = sim.ranking_novo()[-1]
        sim.responder(ultima, Resposta.ACEITAR)
        sim.conferir()
