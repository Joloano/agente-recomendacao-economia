"""Envio de e-mail (padrão Adapter): uma interface, várias implementações.

- `EnviadorSmtp`: qualquer servidor SMTP. Também serve para os provedores transacionais
  (Amazon SES, Brevo, Resend, Postmark), que oferecem relay SMTP com credenciais próprias.
- `EnviadorMemoria`: guarda as mensagens numa lista; usado nos testes.
"""

import logging
import smtplib
import ssl
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.core.config import Configuracoes

log = logging.getLogger(__name__)

PORTA_SMTPS = 465


@dataclass(frozen=True, slots=True)
class Mensagem:
    para: str
    assunto: str
    html: str
    texto: str


class FalhaEnvioEmail(Exception):
    """O provedor recusou ou não respondeu."""


class EnviadorEmail(ABC):
    @abstractmethod
    def enviar(self, mensagem: Mensagem) -> None: ...


class EnviadorMemoria(EnviadorEmail):
    def __init__(self) -> None:
        self.enviadas: list[Mensagem] = []

    def enviar(self, mensagem: Mensagem) -> None:
        self.enviadas.append(mensagem)


class EnviadorSmtp(EnviadorEmail):
    def __init__(self, config: Configuracoes) -> None:
        self._config = config

    def _montar(self, mensagem: Mensagem) -> EmailMessage:
        config = self._config
        email = EmailMessage()
        email["Subject"] = mensagem.assunto
        email["From"] = formataddr((config.nome_app, str(config.email_remetente)))
        email["To"] = mensagem.para
        email["Message-ID"] = make_msgid(domain=str(config.email_remetente).split("@")[-1])
        email.set_content(mensagem.texto)
        email.add_alternative(mensagem.html, subtype="html")
        return email

    def enviar(self, mensagem: Mensagem) -> None:
        config = self._config
        contexto = ssl.create_default_context()
        try:
            if config.smtp_porta == PORTA_SMTPS:
                cliente: smtplib.SMTP = smtplib.SMTP_SSL(
                    config.smtp_host, config.smtp_porta, timeout=config.smtp_timeout_s,
                    context=contexto,
                )  # fmt: skip
            else:
                cliente = smtplib.SMTP(
                    config.smtp_host, config.smtp_porta, timeout=config.smtp_timeout_s
                )
            with cliente:
                if config.smtp_tls and config.smtp_porta != PORTA_SMTPS:
                    cliente.starttls(context=contexto)
                if config.smtp_usuario:
                    cliente.login(config.smtp_usuario, config.smtp_senha.get_secret_value())
                cliente.send_message(self._montar(mensagem))
        except (smtplib.SMTPException, OSError) as erro:
            # O destinatário não vai para o log (LGPD): só o assunto e o motivo.
            log.warning("Falha ao enviar e-mail %r: %s", mensagem.assunto, erro)
            raise FalhaEnvioEmail(str(erro)) from erro


def criar_enviador(config: Configuracoes) -> EnviadorEmail:
    """Factory: escolhe a implementação pela configuração `EMAIL_PROVEDOR`."""
    if config.email_provedor == "memoria":
        return EnviadorMemoria()
    return EnviadorSmtp(config)
