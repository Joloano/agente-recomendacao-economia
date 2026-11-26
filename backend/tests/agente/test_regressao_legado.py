"""Regressão: o novo núcleo reproduz o agente original (legado/agente_energia.py) em R01–R10."""

import importlib.util
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.agente import AgenteRecomendador, Essencialidade, Oportunidade, Pesos, Recurso, Resposta

RAIZ = Path(__file__).resolve().parents[3]
TOLERANCIA = Decimal("0.000001")


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


def _ranking_legado(
    registros: list[dict[str, Any]], pendentes: list[str]
) -> list[tuple[str, float]]:
    percepcao = legado.perceber(registros)
    estado = legado.criar_estado(percepcao)
    estado["pendentes"] = list(pendentes)
    ordenadas = legado.ordenar_recomendacoes(legado.gerar_recomendacoes(estado, percepcao))
    return [(r["oportunidade"]["equipamento_id"], r["utilidade"]) for r in ordenadas]


@pytest.mark.parametrize("residencia", RESIDENCIAS)
def test_mesma_ordem_e_utilidade_do_original(residencia: str) -> None:
    registros = legado.selecionar_residencia(REGISTROS, residencia)
    oportunidades, pesos = _converter(registros)
    agente = AgenteRecomendador()
    estado = agente.perceber(oportunidades)

    novo = agente.recomendar(oportunidades, pesos, estado)
    original = _ranking_legado(registros, sorted(estado.pendentes))

    assert [r.oportunidade.id for r in novo] == [id_ for id_, _ in original]
    for recomendacao, (_, utilidade) in zip(novo, original, strict=True):
        assert abs(recomendacao.utilidade - _d(utilidade)) < TOLERANCIA


@pytest.mark.parametrize("residencia", RESIDENCIAS)
def test_aceitar_tudo_chega_ao_mesmo_consumo_final(residencia: str) -> None:
    registros = legado.selecionar_residencia(REGISTROS, residencia)
    oportunidades, _ = _converter(registros)
    agente = AgenteRecomendador()
    estado = agente.perceber(oportunidades)
    estado_legado = legado.criar_estado(legado.perceber(registros))
    estado_legado["pendentes"] = sorted(estado.pendentes)

    for op in oportunidades:
        if op.id in estado.pendentes:
            agente.responder(estado, op, Resposta.ACEITAR)
            original = next(r for r in registros if r["equipamento_id"] == op.id)
            legado.registrar_feedback(estado_legado, original, "aceitar")

    final = estado.consumo_estimado[Recurso.ENERGIA]
    assert abs(final - _d(estado_legado["consumo_estimado_kwh"])) < Decimal("0.001")
