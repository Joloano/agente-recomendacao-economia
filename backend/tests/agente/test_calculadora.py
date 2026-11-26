from decimal import Decimal

import pytest

from app.agente import CalculadoraUtilidade, Criterio, Notas, Pesos, Recomendacao
from tests.agente.construtor import PESOS_EQUILIBRADOS, oportunidade

calc = CalculadoraUtilidade()


def test_maior_economia_recebe_nota_5_e_conforto_e_esforco_sao_invertidos() -> None:
    notas = calc.notas(
        oportunidade(economia_potencial="0.6", impacto_conforto=1, esforco=5, flexibilidade=4),
        maior_economia=Decimal("0.6"),
    )

    assert notas == Notas(Decimal(5), Decimal(5), Decimal(4), Decimal(1))


def test_nota_de_economia_e_proporcional_a_maior() -> None:
    notas = calc.notas(oportunidade(economia_potencial="0.3"), maior_economia=Decimal("0.6"))

    assert notas.economia == Decimal(3)


def test_sem_economia_elegivel_a_nota_minima_e_1() -> None:
    assert calc.notas(oportunidade(), maior_economia=Decimal(0)).economia == Decimal(1)


def test_utilidade_e_a_soma_ponderada_das_notas() -> None:
    pesos = Pesos(Decimal("0.4"), Decimal("0.3"), Decimal("0.2"), Decimal("0.1"))
    notas = Notas(Decimal(5), Decimal(4), Decimal(3), Decimal(2))

    contribuicoes = calc.contribuicoes(notas, pesos)

    assert dict(contribuicoes)[Criterio.ECONOMIA] == Decimal("2.0")
    assert calc.utilidade(contribuicoes) == Decimal("4.0")


@pytest.mark.parametrize("nota", [1, 5])
def test_utilidade_fica_entre_1_e_5_quando_pesos_somam_1(nota: int) -> None:
    notas = Notas(*(Decimal(nota),) * 4)

    utilidade = calc.utilidade(calc.contribuicoes(notas, PESOS_EQUILIBRADOS))

    assert utilidade == Decimal(nota)


def _rec(id_: str, utilidade: str, economia: str, ordem: int) -> Recomendacao:
    op = oportunidade(id=id_, economia_potencial=economia, ordem=ordem)
    # A nota de economia acompanha a economia bruta, como acontece dentro de um recurso.
    notas = Notas(Decimal(economia) * 10, Decimal(1), Decimal(1), Decimal(1))
    return Recomendacao(op, notas, Decimal(utilidade), (), "")


def test_ordena_por_utilidade_depois_economia_depois_ordem_de_cadastro() -> None:
    recomendacoes = [
        _rec("C", "3.0", "0.1", ordem=2),
        _rec("A", "4.0", "0.1", ordem=3),
        _rec("D", "3.0", "0.1", ordem=1),
        _rec("B", "3.0", "0.5", ordem=4),
    ]

    assert [r.oportunidade.id for r in calc.ordenar(recomendacoes)] == ["A", "B", "D", "C"]


def test_diferencas_menores_que_a_precisao_contam_como_empate() -> None:
    quase_iguais = [_rec("X", "3.0000001", "0.1", 1), _rec("Y", "3.0", "0.9", 2)]

    assert [r.oportunidade.id for r in calc.ordenar(quase_iguais)] == ["Y", "X"]
