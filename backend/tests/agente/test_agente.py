from decimal import Decimal

import pytest

from app.agente import (
    FABRICA_PADRAO,
    AgenteRecomendador,
    CalculadoraUtilidade,
    ErroAgente,
    Essencialidade,
    EstrategiaEnergia,
    FabricaEstrategia,
    Recomendacao,
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
    assert sum(v for _, v in recomendacoes[0].contribuicoes) == recomendacoes[0].utilidade
    assert hash(recomendacoes[0])


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


def test_recurso_sem_estrategia_ou_repetido_e_recusado() -> None:
    with pytest.raises(ErroAgente, match="não suportado"):
        AgenteRecomendador([Recurso.AGUA])
    with pytest.raises(ErroAgente, match="ao menos um"):
        AgenteRecomendador([])
    with pytest.raises(ErroAgente, match="repetidos"):
        AgenteRecomendador([Recurso.ENERGIA, Recurso.ENERGIA])


def test_ids_repetidos_sao_recusados(agente: AgenteRecomendador) -> None:
    with pytest.raises(ErroAgente, match="repetidos: E2"):
        agente.perceber([*CASA, CASA[1]])


def test_explicacao_so_para_recursos_do_agente(agente: AgenteRecomendador) -> None:
    with pytest.raises(ErroAgente, match="não trata"):
        agente.explicar_inelegibilidade(oportunidade(recurso=Recurso.AGUA))


class EstrategiaAguaFalsa(EstrategiaEnergia):
    recurso = Recurso.AGUA


FABRICA_COM_AGUA = FABRICA_PADRAO.com(EstrategiaAguaFalsa)


def test_fabrica_e_imutavel_e_recusa_duplicados() -> None:
    assert FABRICA_PADRAO.recursos == {Recurso.ENERGIA}
    assert FABRICA_COM_AGUA.recursos == {Recurso.ENERGIA, Recurso.AGUA}
    with pytest.raises(ErroAgente, match="duplicada"):
        FabricaEstrategia([EstrategiaEnergia, EstrategiaEnergia])


def test_varios_recursos_numa_lista_unica() -> None:
    agente = AgenteRecomendador([Recurso.ENERGIA, Recurso.AGUA], fabrica=FABRICA_COM_AGUA)
    agua = oportunidade(id="A1", recurso=Recurso.AGUA, economia_potencial="50")
    estado = agente.perceber([*CASA, agua])

    ids = [r.oportunidade.id for r in agente.recomendar([*CASA, agua], PESOS_EQUILIBRADOS, estado)]

    assert set(ids) == {"E2", "E3", "E4", "A1"}
    assert estado.consumo_inicial[Recurso.AGUA] == agua.consumo_diario


def test_desempate_entre_recursos_usa_nota_normalizada_e_nao_valor_bruto() -> None:
    agente = AgenteRecomendador([Recurso.ENERGIA, Recurso.AGUA], fabrica=FABRICA_COM_AGUA)
    # Mesmas notas nos dois recursos: cada uma é a maior economia do seu recurso (nota 5).
    energia = oportunidade(id="E", economia_potencial="0.4", ordem=1)
    agua = oportunidade(id="A", recurso=Recurso.AGUA, economia_potencial="50", ordem=0)
    estado = agente.perceber([energia, agua])

    ordem = [
        r.oportunidade.id for r in agente.recomendar([energia, agua], PESOS_EQUILIBRADOS, estado)
    ]

    # Empate total: decide a ordem dos recursos (energia primeiro), não os 50 L contra 0,4 kWh.
    assert ordem == ["E", "A"]


def test_calculadora_injetada_e_usada_pelas_estrategias() -> None:
    class CalculadoraEspia(CalculadoraUtilidade):
        chamadas = 0

        def notas(self, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
            CalculadoraEspia.chamadas += 1
            return super().notas(*args, **kwargs)  # type: ignore[arg-type]

    agente = AgenteRecomendador(calculadora=CalculadoraEspia())
    recomendacoes: list[Recomendacao] = agente.recomendar(
        CASA, PESOS_EQUILIBRADOS, agente.perceber(CASA)
    )

    assert CalculadoraEspia.chamadas == len(recomendacoes) == 3
