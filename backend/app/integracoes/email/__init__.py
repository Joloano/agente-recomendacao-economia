"""Envio de e-mails transacionais (ver docs/email.md)."""

from typing import Annotated

from fastapi import Depends

from app.core.config import Configuracoes, obter_configuracoes
from app.integracoes.email.enviadores import (
    EnviadorEmail,
    EnviadorMemoria,
    EnviadorSmtp,
    FalhaEnvioEmail,
    Mensagem,
    criar_enviador,
)
from app.integracoes.email.servico import ServicoEmail


def obter_servico_email(
    config: Annotated[Configuracoes, Depends(obter_configuracoes)],
) -> ServicoEmail:
    """Dependência do FastAPI; nos testes, troque por um ServicoEmail com EnviadorMemoria."""
    return ServicoEmail(criar_enviador(config), config)


__all__ = [
    "EnviadorEmail",
    "EnviadorMemoria",
    "EnviadorSmtp",
    "FalhaEnvioEmail",
    "Mensagem",
    "ServicoEmail",
    "criar_enviador",
    "obter_servico_email",
]
