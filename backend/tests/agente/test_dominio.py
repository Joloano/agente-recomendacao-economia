from dataclasses import replace
from decimal import Decimal

import pytest

from app.agente import Criterio, ErroAgente, Pesos, Recurso
from tests.agente.construtor import oportunidade


def test_pesos_precisam_somar_um() -> None:
    with pytest.raises(ErroAgente, match="somar 1"):
        Pesos(Decimal("0.5"), Decimal("0.5"), Decimal("0.5"), Decimal(0))


def test_pesos_fora_do_intervalo_sao_recusados() -> None:
    with pytest.raises(ErroAgente, match="entre 0 e 1"):
        Pesos(Decimal("1.5"), Decimal("-0.5"), Decimal(0), Decimal(0))


def test_pesos_aceitam_tolerancia_de_arredondamento() -> None:
    pesos = Pesos(Decimal("0.3333"), Decimal("0.3333"), Decimal("0.3333"), Decimal(0))

    assert pesos.como_dict()[Criterio.ECONOMIA] == Decimal("0.3333")


@pytest.mark.parametrize("campo", ["impacto_conforto", "flexibilidade", "esforco"])
@pytest.mark.parametrize("valor", [0, 6])
def test_escalas_fora_de_1_a_5_sao_recusadas(campo: str, valor: int) -> None:
    with pytest.raises(ErroAgente, match=campo):
        oportunidade(**{campo: valor})


def test_consumo_negativo_e_recusado() -> None:
    with pytest.raises(ErroAgente, match="negativos"):
        oportunidade(economia_potencial=-1)


def test_unidade_por_recurso() -> None:
    assert Recurso.ENERGIA.unidade == "kWh"
    assert Recurso.AGUA.unidade == "L"


def test_tolerancia_da_soma_dos_pesos_e_inclusiva_ate_0_001() -> None:
    Pesos(Decimal("0.251"), Decimal("0.25"), Decimal("0.25"), Decimal("0.25"))  # soma 1,001
    with pytest.raises(ErroAgente, match="somar 1"):
        Pesos(Decimal("0.2511"), Decimal("0.25"), Decimal("0.25"), Decimal("0.25"))


@pytest.mark.parametrize("valor", [0.5, Decimal("NaN"), Decimal("Infinity")])
def test_economia_precisa_ser_decimal_finito(valor: object) -> None:
    with pytest.raises(ErroAgente, match="economia_potencial deve ser um Decimal finito"):
        replace(oportunidade(), economia_potencial=valor)  # type: ignore[arg-type]


def test_peso_float_e_recusado() -> None:
    with pytest.raises(ErroAgente, match="peso_economia deve ser um Decimal finito"):
        Pesos(0.5, Decimal("0.5"), Decimal(0), Decimal(0))  # type: ignore[arg-type]
