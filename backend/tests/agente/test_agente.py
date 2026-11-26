from decimal import Decimal

import pytest

from app.agente import (
    AgenteRecomendador,
    ErroAgente,
    Essencialidade,
    EstrategiaEnergia,
    FabricaEstrategia,
    RecomendacaoJaRespondida,
    Recurso,
    Resposta,
)
from tests.agente.construtor import PESOS_EQUILIBRADOS, oportunidade

CASA = [
    oportunidade(id="E1", nome="Geladeira", categoria="cozinha", consumo_diario="4",
                 essencialidade=Essencialidade.ESSENCIAL, economia_potencial=0, ordem=1),
    oportunidade(id="E2", nome="Lavadora", categoria="lavanderia", consumo_diario="0.7",
                 economia_potencial="0.16", ordem=2),
    oportunidade(id="E3", nome="TV", categoria="entretenimento", consumo_diario="0.5",
                 economia_potencial="0.3", impacto_conforto=1, esforco=1, ordem=3),
    oportunidade(id="E4", nome="Aquecedor", categoria="outra", consumo_diario="2",
                 economia_potencial="0.4", ordem=4),
]  # fmt: skip


@pytest.fixture
def agente() -> AgenteRecomendador:
    return AgenteRecomendador()


def test_percebe_consumo_total_e_pendentes_elegiveis(agente: AgenteRecomendador) -> None:
    estado = agente.perceber(CASA)

    assert estado.consumo_inicial[Recurso.ENERGIA] == Decimal("7.2")
    assert estado.pendentes == {"E2", "E3", "E4"}


def test_recomenda_em_ordem_com_acao_e_contribuicoes(agente: AgenteRecomendador) -> None:
    estado = agente.perceber(CASA)

    recomendacoes = agente.recomendar(CASA, PESOS_EQUILIBRADOS, estado)

    assert [r.oportunidade.id for r in recomendacoes] == ["E3", "E4", "E2"]
    assert recomendacoes[0].acao.startswith("Desligar a TV")
    assert recomendacoes[1].acao == EstrategiaEnergia.ACAO_PADRAO
    assert sum(recomendacoes[0].contribuicoes.values()) == recomendacoes[0].utilidade


def test_aceitar_reduz_consumo_e_tira_dos_pendentes(agente: AgenteRecomendador) -> None:
    estado = agente.perceber(CASA)

    registro = agente.responder(estado, CASA[2], Resposta.ACEITAR)

    assert registro.consumo_depois == Decimal("6.9")
    assert estado.economia_total(Recurso.ENERGIA) == Decimal("0.3")
    assert [r.oportunidade.id for r in agente.recomendar(CASA, PESOS_EQUILIBRADOS, estado)] == [
        "E4",
        "E2",
    ]


def test_rejeitar_mantem_consumo(agente: AgenteRecomendador) -> None:
    estado = agente.perceber(CASA)

    agente.responder(estado, CASA[1], Resposta.REJEITAR)

    assert estado.consumo_estimado[Recurso.ENERGIA] == Decimal("7.2")
    assert estado.rejeitadas == ["E2"]


def test_nota_de_economia_nao_muda_depois_de_responder(agente: AgenteRecomendador) -> None:
    estado = agente.perceber(CASA)
    antes = {
        r.oportunidade.id: r.utilidade for r in agente.recomendar(CASA, PESOS_EQUILIBRADOS, estado)
    }

    agente.responder(estado, CASA[3], Resposta.ACEITAR)  # a de maior economia sai
    depois = {
        r.oportunidade.id: r.utilidade for r in agente.recomendar(CASA, PESOS_EQUILIBRADOS, estado)
    }

    assert depois["E2"] == antes["E2"]


def test_feedback_repetido_nao_e_processado(agente: AgenteRecomendador) -> None:
    estado = agente.perceber(CASA)
    agente.responder(estado, CASA[3], Resposta.ACEITAR)

    with pytest.raises(RecomendacaoJaRespondida):
        agente.responder(estado, CASA[3], Resposta.ACEITAR)
    assert estado.consumo_estimado[Recurso.ENERGIA] == Decimal("6.8")


def test_consumo_estimado_nunca_fica_negativo(agente: AgenteRecomendador) -> None:
    exagerada = oportunidade(consumo_diario="0.1", economia_potencial="5")
    estado = agente.perceber([exagerada])

    agente.responder(estado, exagerada, Resposta.ACEITAR)

    assert estado.consumo_estimado[Recurso.ENERGIA] == Decimal(0)
    assert estado.encerrada


def test_inelegivel_nunca_entra_nem_pode_ser_respondida(agente: AgenteRecomendador) -> None:
    estado = agente.perceber(CASA)

    with pytest.raises(RecomendacaoJaRespondida):
        agente.responder(estado, CASA[0], Resposta.ACEITAR)
    assert agente.explicar_inelegibilidade(CASA[0]) == "não há economia possível"


def test_recurso_sem_estrategia_registrada_e_recusado() -> None:
    with pytest.raises(ErroAgente, match="não suportado"):
        AgenteRecomendador([Recurso.AGUA])
    with pytest.raises(ErroAgente, match="ao menos um"):
        AgenteRecomendador([])


def test_fabrica_permite_registrar_novos_recursos() -> None:
    class EstrategiaAguaFalsa(EstrategiaEnergia):
        recurso = Recurso.AGUA

    FabricaEstrategia.registrar(EstrategiaAguaFalsa)
    try:
        agente = AgenteRecomendador([Recurso.ENERGIA, Recurso.AGUA])
        agua = oportunidade(id="A1", recurso=Recurso.AGUA, economia_potencial="50")
        estado = agente.perceber([*CASA, agua])

        ids = [
            r.oportunidade.id for r in agente.recomendar([*CASA, agua], PESOS_EQUILIBRADOS, estado)
        ]

        assert "A1" in ids
        assert estado.consumo_inicial[Recurso.AGUA] == agua.consumo_diario
    finally:
        FabricaEstrategia._registro.pop(Recurso.AGUA)
