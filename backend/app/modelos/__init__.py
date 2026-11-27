"""Modelos SQLAlchemy. Importar este pacote registra todas as tabelas em `Base.metadata`."""

from app.modelos.base import Base
from app.modelos.enums import Papel, RecursoSimulacao, StatusRecomendacao, StatusSimulacao
from app.modelos.equipamento import Categoria, Equipamento
from app.modelos.residencia import Preferencia, Residencia
from app.modelos.simulacao import Feedback, Recomendacao, Simulacao
from app.modelos.tentativa import TentativaAcesso
from app.modelos.usuario import Usuario

__all__ = [
    "Base",
    "Categoria",
    "Equipamento",
    "Feedback",
    "Papel",
    "Preferencia",
    "Recomendacao",
    "RecursoSimulacao",
    "Residencia",
    "Simulacao",
    "StatusRecomendacao",
    "StatusSimulacao",
    "TentativaAcesso",
    "Usuario",
]
