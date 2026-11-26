"""Builder de dados de teste: monta oportunidades válidas e muda só o que importa."""

from dataclasses import replace
from decimal import Decimal
from typing import Any

from app.agente import Essencialidade, Oportunidade, Pesos, Recurso

_BASE = Oportunidade(
    id="E01",
    nome="Máquina de lavar",
    categoria="lavanderia",
    recurso=Recurso.ENERGIA,
    consumo_diario=Decimal("0.7"),
    reducao_uso=True,
    essencialidade=Essencialidade.IMPORTANTE,
    impacto_conforto=2,
    flexibilidade=3,
    esforco=2,
    economia_potencial=Decimal("0.16"),
)

PESOS_EQUILIBRADOS = Pesos(
    economia=Decimal("0.25"),
    conforto=Decimal("0.25"),
    flexibilidade=Decimal("0.25"),
    baixo_esforco=Decimal("0.25"),
)


def oportunidade(**mudancas: Any) -> Oportunidade:
    for campo in ("consumo_diario", "economia_potencial"):
        if campo in mudancas:
            mudancas[campo] = Decimal(str(mudancas[campo]))
    return replace(_BASE, **mudancas)
