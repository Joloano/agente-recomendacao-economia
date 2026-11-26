"""Notas de 1 a 5 por critério e utilidade ponderada."""

from collections.abc import Iterable
from decimal import Decimal

from app.agente.dominio import Criterio, Notas, Oportunidade, Pesos, Recomendacao

ESCALA = Decimal(6)
NOTA_MINIMA = Decimal(1)
AMPLITUDE_NOTA = Decimal(4)
CASAS_DESEMPATE = Decimal("0.000001")


class CalculadoraUtilidade:
    def notas(self, oportunidade: Oportunidade, maior_economia: Decimal) -> Notas:
        proporcao = (
            oportunidade.economia_potencial / maior_economia if maior_economia > 0 else Decimal(0)
        )
        return Notas(
            economia=NOTA_MINIMA + AMPLITUDE_NOTA * proporcao,
            conforto=ESCALA - oportunidade.impacto_conforto,
            flexibilidade=Decimal(oportunidade.flexibilidade),
            baixo_esforco=ESCALA - oportunidade.esforco,
        )

    def contribuicoes(self, notas: Notas, pesos: Pesos) -> dict[Criterio, Decimal]:
        valores_notas = notas.como_dict()
        return {
            criterio: peso * valores_notas[criterio] for criterio, peso in pesos.como_dict().items()
        }

    def utilidade(self, contribuicoes: dict[Criterio, Decimal]) -> Decimal:
        return sum(contribuicoes.values(), Decimal(0))

    def ordenar(self, recomendacoes: Iterable[Recomendacao]) -> list[Recomendacao]:
        """Maior utilidade; empate → maior economia; persistindo → ordem de cadastro."""
        return sorted(
            recomendacoes,
            key=lambda r: (
                -r.utilidade.quantize(CASAS_DESEMPATE),
                -r.oportunidade.economia_potencial,
                r.oportunidade.ordem,
            ),
        )
