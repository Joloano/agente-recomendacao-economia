"""Estado da simulação: memória do agente entre as respostas do usuário."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from app.agente.dominio import ErroAgente, Oportunidade, Recurso


class Resposta(StrEnum):
    ACEITAR = "aceitar"
    REJEITAR = "rejeitar"


class RecomendacaoJaRespondida(ErroAgente):
    """A recomendação já foi aceita ou rejeitada; não é processada de novo."""


@dataclass(frozen=True, slots=True)
class RegistroFeedback:
    oportunidade_id: str
    resposta: Resposta
    consumo_antes: Decimal
    consumo_depois: Decimal


@dataclass
class EstadoSimulacao:
    consumo_inicial: dict[Recurso, Decimal]
    consumo_estimado: dict[Recurso, Decimal]
    pendentes: set[str]
    aceitas: list[str] = field(default_factory=list)
    rejeitadas: list[str] = field(default_factory=list)
    historico: list[RegistroFeedback] = field(default_factory=list)

    @property
    def encerrada(self) -> bool:
        return not self.pendentes

    def economia_total(self, recurso: Recurso) -> Decimal:
        return self.consumo_inicial[recurso] - self.consumo_estimado[recurso]

    def registrar(self, oportunidade: Oportunidade, resposta: Resposta) -> RegistroFeedback:
        if oportunidade.id not in self.pendentes:
            raise RecomendacaoJaRespondida(f"{oportunidade.nome} já foi respondida.")
        recurso = oportunidade.recurso
        antes = self.consumo_estimado[recurso]
        if resposta is Resposta.ACEITAR:
            # O consumo estimado nunca fica negativo.
            self.consumo_estimado[recurso] = max(
                Decimal(0), antes - oportunidade.economia_potencial
            )
            self.aceitas.append(oportunidade.id)
        else:
            self.rejeitadas.append(oportunidade.id)
        self.pendentes.discard(oportunidade.id)
        registro = RegistroFeedback(
            oportunidade.id, resposta, antes, self.consumo_estimado[recurso]
        )
        self.historico.append(registro)
        return registro
