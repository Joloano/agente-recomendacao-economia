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
from email.utils import formataddr, formatdate, make_msgid

from email_validator import EmailNotValidError, validate_email

from app.core.config import Configuracoes

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Mensagem:
    para: str
    assunto: str
    html: str
    texto: str
    modelo: str = "avulso"

    def __post_init__(self) -> None:
        # Um único destinatário válido: "a@x.com, b@y.com" ou quebras de linha não passam.
        try:
            validate_email(self.para, check_deliverability=False)
        except EmailNotValidError as erro:
            raise ValueError("Destinatário inválido.") from erro
        if any(c in self.assunto for c in "\r\n"):
            raise ValueError("O assunto não pode ter quebras de linha.")


class FalhaEnvioEmail(Exception):
    """O provedor recusou ou não respondeu. A mensagem nunca traz dados pessoais."""


def _descrever(erro: Exception) -> str:
    """Tipo do erro e código SMTP, sem o texto (que pode trazer o endereço do destinatário)."""
    codigo = getattr(erro, "smtp_code", None)
    return f"{type(erro).__name__}" + (f" (código {codigo})" if codigo else "")


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
        email["Date"] = formatdate(localtime=True)
        email["Message-ID"] = make_msgid(domain=str(config.email_remetente).split("@")[-1])
        email.set_content(mensagem.texto)
        email.add_alternative(mensagem.html, subtype="html")
        return email

    def _conectar(self) -> smtplib.SMTP:
        config = self._config
        contexto = ssl.create_default_context()
        if config.smtp_seguranca == "ssl":
            return smtplib.SMTP_SSL(
                config.smtp_host, config.smtp_porta, timeout=config.smtp_timeout_s, context=contexto
            )
        cliente = smtplib.SMTP(config.smtp_host, config.smtp_porta, timeout=config.smtp_timeout_s)
        if config.smtp_seguranca == "starttls":
            cliente.starttls(context=contexto)
        return cliente

    def enviar(self, mensagem: Mensagem) -> None:
        config = self._config
        try:
            email = self._montar(mensagem)
            with self._conectar() as cliente:
                if config.smtp_usuario:
                    cliente.login(config.smtp_usuario, config.smtp_senha.get_secret_value())
                cliente.send_message(email)
        except (smtplib.SMTPException, OSError, ValueError) as erro:
            raise FalhaEnvioEmail(_descrever(erro)) from None


def criar_enviador(config: Configuracoes) -> EnviadorEmail:
    """Factory: escolhe a implementação pela configuração `EMAIL_PROVEDOR`."""
    if config.email_provedor == "memoria":
        return EnviadorMemoria()
    return EnviadorSmtp(config)
