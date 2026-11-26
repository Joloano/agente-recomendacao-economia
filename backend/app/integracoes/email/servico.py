"""E-mails do produto, montados a partir dos modelos em `modelos/`.

O envio roda fora da requisição (`BackgroundTasks` no MVP; fila na v1.1, #96): a resposta
HTTP não espera o servidor de e-mail, e uma falha de envio não derruba a operação.
"""

import logging
from collections.abc import Mapping
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.core.config import Configuracoes
from app.integracoes.email.enviadores import EnviadorEmail, FalhaEnvioEmail, Mensagem

log = logging.getLogger(__name__)

PASTA_MODELOS = Path(__file__).parent / "modelos"


@cache
def _ambiente() -> Environment:
    # autoescape: um nome como "<script>" chega ao e-mail como texto, nunca como HTML.
    return Environment(
        loader=FileSystemLoader(PASTA_MODELOS),
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


class ServicoEmail:
    def __init__(self, enviador: EnviadorEmail, config: Configuracoes) -> None:
        self._enviador = enviador
        self._config = config

    def _validar_link(self, link: str) -> None:
        """Só links do próprio sistema: bloqueia `javascript:` e endereços de terceiros."""
        alvo, base = urlparse(link), urlparse(self._config.url_frontend)
        if (alvo.scheme, alvo.netloc) != (base.scheme, base.netloc):
            raise ValueError("O link do e-mail precisa apontar para a URL_FRONTEND.")

    def montar(self, modelo: str, para: str, assunto: str, **dados: Any) -> Mensagem:
        if "link" in dados:
            self._validar_link(str(dados["link"]))
        assunto = " ".join(assunto.split())  # sem quebras de linha (injeção de cabeçalho)
        contexto: Mapping[str, Any] = {
            "nome_app": self._config.nome_app,
            "url_frontend": self._config.url_frontend,
            "assunto": assunto,
            **dados,
        }
        ambiente = _ambiente()
        return Mensagem(
            para=para,
            assunto=assunto,
            html=ambiente.get_template(f"{modelo}.html").render(contexto),
            texto=ambiente.get_template(f"{modelo}.txt").render(contexto),
            modelo=modelo,
        )

    def enviar(self, mensagem: Mensagem) -> bool:
        """Envia e devolve se deu certo. Pensado para rodar em segundo plano: não levanta."""
        try:
            self._enviador.enviar(mensagem)
        except FalhaEnvioEmail as erro:
            # Só o nome do modelo e o tipo do erro: assunto e destinatário podem ter dados pessoais.
            log.warning("E-mail do modelo %s não enviado: %s", mensagem.modelo, erro)
            return False
        return True

    # ---------- e-mails do produto ----------
    def boas_vindas(self, para: str, nome: str) -> Mensagem:
        return self.montar(
            "boas_vindas", para, f"Boas-vindas ao {self._config.nome_app}", nome=nome
        )

    def verificacao(self, para: str, nome: str, link: str, validade_horas: int) -> Mensagem:
        return self.montar(
            "verificacao_email", para, "Confirme seu e-mail",
            nome=nome, link=link, validade_horas=validade_horas,
        )  # fmt: skip

    def recuperacao_senha(self, para: str, nome: str, link: str, validade_minutos: int) -> Mensagem:
        return self.montar(
            "recuperacao_senha", para, "Redefinição de senha",
            nome=nome, link=link, validade_minutos=validade_minutos,
        )  # fmt: skip

    def alerta(self, para: str, nome: str, titulo: str, descricao: str, link: str) -> Mensagem:
        return self.montar(
            "alerta", para, titulo, nome=nome, titulo=titulo, descricao=descricao, link=link
        )
