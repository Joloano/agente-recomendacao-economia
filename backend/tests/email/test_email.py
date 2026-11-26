import smtplib
from email.message import EmailMessage
from typing import Any, ClassVar

import pytest

from app.core.config import Ambiente, Configuracoes
from app.integracoes.email import (
    EnviadorMemoria,
    EnviadorSmtp,
    FalhaEnvioEmail,
    Mensagem,
    ServicoEmail,
    criar_enviador,
)

CONFIG = Configuracoes(
    _env_file=None,
    ambiente=Ambiente.TESTE,
    nome_app="Agente de Economia",
    url_frontend="https://app.exemplo.com",
    email_remetente="nao-responda@exemplo.com",
)


@pytest.fixture
def caixa() -> EnviadorMemoria:
    return EnviadorMemoria()


@pytest.fixture
def servico(caixa: EnviadorMemoria) -> ServicoEmail:
    return ServicoEmail(caixa, CONFIG)


# ---------- modelos ----------
def test_boas_vindas_em_html_e_texto(servico: ServicoEmail) -> None:
    mensagem = servico.boas_vindas("ana@exemplo.com", "Ana")

    assert mensagem.assunto == "Boas-vindas ao Agente de Economia"
    assert "Olá, Ana!" in mensagem.html and "Olá, Ana!" in mensagem.texto
    assert 'lang="pt-BR"' in mensagem.html
    assert "https://app.exemplo.com/inicio" in mensagem.html
    assert "<" not in mensagem.texto


def test_nome_com_html_e_escapado(servico: ServicoEmail) -> None:
    mensagem = servico.boas_vindas("x@exemplo.com", '<script>alert("x")</script>')

    assert "<script>" not in mensagem.html
    assert "&lt;script&gt;" in mensagem.html


@pytest.mark.parametrize(
    ("montar", "trechos"),
    [
        (
            lambda s: s.verificacao("a@x.com", "Ana", "https://app/v?t=abc", 24),
            ["Confirme seu e-mail", "https://app/v?t=abc", "24 horas"],
        ),
        (
            lambda s: s.recuperacao_senha("a@x.com", "Ana", "https://app/r?t=abc", 30),
            ["Redefinição de senha", "https://app/r?t=abc", "30 minutos", "Se não foi você"],
        ),
        (
            lambda s: s.alerta(
                "a@x.com", "Ana", "Meta ultrapassada", "Hoje: 9,2 kWh", "https://app"
            ),
            ["Meta ultrapassada", "Hoje: 9,2 kWh"],
        ),
    ],
)
def test_cada_modelo_traz_o_essencial(
    servico: ServicoEmail, montar: Any, trechos: list[str]
) -> None:
    mensagem: Mensagem = montar(servico)

    for trecho in trechos:
        assert trecho in mensagem.assunto + mensagem.html
        assert trecho in mensagem.assunto + mensagem.texto


def test_variavel_faltando_no_modelo_e_erro_e_nao_texto_vazio(servico: ServicoEmail) -> None:
    with pytest.raises(Exception, match="link"):
        servico.montar("recuperacao_senha", "a@x.com", "Assunto", nome="Ana", validade_minutos=5)


# ---------- envio ----------
def test_enviar_entrega_ao_enviador(servico: ServicoEmail, caixa: EnviadorMemoria) -> None:
    assert servico.enviar(servico.boas_vindas("ana@exemplo.com", "Ana"))
    assert [m.para for m in caixa.enviadas] == ["ana@exemplo.com"]


def test_falha_de_envio_nao_propaga(caplog: pytest.LogCaptureFixture) -> None:
    class Quebrado(EnviadorMemoria):
        def enviar(self, mensagem: Mensagem) -> None:
            raise FalhaEnvioEmail("servidor fora")

    servico = ServicoEmail(Quebrado(), CONFIG)

    assert servico.enviar(servico.boas_vindas("ana@exemplo.com", "Ana")) is False
    assert "ana@exemplo.com" not in caplog.text  # destinatário fora do log (LGPD)


class SmtpFalso:
    """Substitui smtplib.SMTP e registra o que foi feito."""

    instancias: ClassVar[list["SmtpFalso"]] = []

    def __init__(self, host: str, porta: int, timeout: float, **_: Any) -> None:
        self.host, self.porta, self.timeout = host, porta, timeout
        self.tls = False
        self.login_feito: tuple[str, str] | None = None
        self.enviada: EmailMessage | None = None
        SmtpFalso.instancias.append(self)

    def __enter__(self) -> "SmtpFalso":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def starttls(self, context: object) -> None:
        self.tls = True

    def login(self, usuario: str, senha: str) -> None:
        self.login_feito = (usuario, senha)

    def send_message(self, mensagem: EmailMessage) -> None:
        self.enviada = mensagem


@pytest.fixture
def smtp_falso(monkeypatch: pytest.MonkeyPatch) -> type[SmtpFalso]:
    SmtpFalso.instancias = []
    monkeypatch.setattr(smtplib, "SMTP", SmtpFalso)
    monkeypatch.setattr(smtplib, "SMTP_SSL", SmtpFalso)
    return SmtpFalso


def test_smtp_com_starttls_login_e_partes_html_e_texto(smtp_falso: type[SmtpFalso]) -> None:
    config = CONFIG.model_copy(
        update={"smtp_host": "smtp.exemplo.com", "smtp_porta": 587, "smtp_tls": True,
                "smtp_usuario": "u", "smtp_senha": CONFIG.smtp_senha.__class__("s")}
    )  # fmt: skip
    servico = ServicoEmail(EnviadorSmtp(config), config)

    assert servico.enviar(servico.boas_vindas("ana@exemplo.com", "Ana"))

    cliente = smtp_falso.instancias[0]
    assert (cliente.host, cliente.porta, cliente.tls) == ("smtp.exemplo.com", 587, True)
    assert cliente.login_feito == ("u", "s")
    assert cliente.enviada is not None
    assert cliente.enviada["To"] == "ana@exemplo.com"
    assert "Agente de Economia" in cliente.enviada["From"]
    tipos = [parte.get_content_type() for parte in cliente.enviada.iter_parts()]
    assert tipos == ["text/plain", "text/html"]


def test_smtp_sem_credenciais_nao_faz_login(smtp_falso: type[SmtpFalso]) -> None:
    EnviadorSmtp(CONFIG).enviar(Mensagem("a@x.com", "Teste", "<p>oi</p>", "oi"))

    assert smtp_falso.instancias[0].login_feito is None
    assert smtp_falso.instancias[0].tls is False


def test_erro_de_conexao_vira_falha_de_envio(monkeypatch: pytest.MonkeyPatch) -> None:
    def recusar(*_: object, **__: object) -> None:
        raise ConnectionRefusedError("recusado")

    monkeypatch.setattr(smtplib, "SMTP", recusar)

    with pytest.raises(FalhaEnvioEmail):
        EnviadorSmtp(CONFIG).enviar(Mensagem("a@x.com", "Teste", "<p>oi</p>", "oi"))


def test_fabrica_escolhe_pelo_provedor() -> None:
    assert isinstance(criar_enviador(CONFIG), EnviadorSmtp)
    memoria = CONFIG.model_copy(update={"email_provedor": "memoria"})
    assert isinstance(criar_enviador(memoria), EnviadorMemoria)
