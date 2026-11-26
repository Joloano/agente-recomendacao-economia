"""Núcleo do agente recomendador: Python puro, sem banco, HTTP ou entrada/saída.

Padrões aplicados (ver docs/padroes-de-projeto.md): Facade (`AgenteRecomendador`),
Strategy + Template Method (`EstrategiaRecurso`), Factory Method (`FabricaEstrategia`)
e Chain of Responsibility (regras de elegibilidade).
"""

from app.agente.agente import AgenteRecomendador
from app.agente.calculadora import CalculadoraUtilidade
from app.agente.dominio import (
    Criterio,
    ErroAgente,
    Essencialidade,
    Notas,
    Oportunidade,
    Pesos,
    Recomendacao,
    Recurso,
)
from app.agente.estrategias import EstrategiaEnergia, EstrategiaRecurso, FabricaEstrategia
from app.agente.simulacao import (
    EstadoSimulacao,
    RecomendacaoJaRespondida,
    RegistroFeedback,
    Resposta,
)

__all__ = [
    "AgenteRecomendador",
    "CalculadoraUtilidade",
    "Criterio",
    "ErroAgente",
    "Essencialidade",
    "EstadoSimulacao",
    "EstrategiaEnergia",
    "EstrategiaRecurso",
    "FabricaEstrategia",
    "Notas",
    "Oportunidade",
    "Pesos",
    "Recomendacao",
    "RecomendacaoJaRespondida",
    "Recurso",
    "RegistroFeedback",
    "Resposta",
]
