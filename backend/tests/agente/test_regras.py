import pytest

from app.agente import Essencialidade
from app.agente.regras import RegraConfortoMaximo, RegraNaoEssencial, montar_cadeia_padrao
from tests.agente.construtor import oportunidade

cadeia = montar_cadeia_padrao()


def test_oportunidade_que_cumpre_tudo_e_elegivel() -> None:
    assert cadeia.avaliar(oportunidade()) is None


@pytest.mark.parametrize(
    ("mudanca", "motivo"),
    [
        ({"reducao_uso": False}, "o uso não pode ser reduzido"),
        ({"economia_potencial": 0}, "não há economia possível"),
        ({"essencialidade": Essencialidade.ESSENCIAL}, "é um equipamento essencial"),
        ({"impacto_conforto": 4}, "o impacto no conforto seria alto demais"),
    ],
)
def test_cada_regra_reprova_com_seu_motivo(mudanca: dict[str, object], motivo: str) -> None:
    assert cadeia.avaliar(oportunidade(**mudanca)) == motivo


def test_conforto_no_limite_de_3_e_aceito() -> None:
    assert cadeia.avaliar(oportunidade(impacto_conforto=3)) is None


def test_primeira_regra_que_reprova_interrompe_a_cadeia() -> None:
    reprovada_duas_vezes = oportunidade(reducao_uso=False, essencialidade=Essencialidade.ESSENCIAL)

    assert cadeia.avaliar(reprovada_duas_vezes) == "o uso não pode ser reduzido"


def test_regras_podem_ser_recombinadas() -> None:
    so_conforto = RegraNaoEssencial()
    so_conforto.encadear(RegraConfortoMaximo())

    assert so_conforto.avaliar(oportunidade(reducao_uso=False)) is None
    assert so_conforto.avaliar(oportunidade(impacto_conforto=5)) is not None
