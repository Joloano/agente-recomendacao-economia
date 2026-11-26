"""Enums de persistência. Os de domínio (Recurso, Essencialidade, Resposta) vêm de app.agente."""

from enum import StrEnum


class Papel(StrEnum):
    ADMIN = "admin"
    CLIENTE = "cliente"


class RecursoSimulacao(StrEnum):
    ENERGIA = "energia"
    AGUA = "agua"
    AMBOS = "ambos"


class StatusSimulacao(StrEnum):
    ATIVA = "ativa"
    ENCERRADA = "encerrada"


class StatusRecomendacao(StrEnum):
    PENDENTE = "pendente"
    ACEITA = "aceita"
    REJEITADA = "rejeitada"
