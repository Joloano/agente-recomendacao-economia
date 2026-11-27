"""Limite de tentativas por janela deslizante, guardado no PostgreSQL (#137).

No banco (e não em memória) para valer entre workers e réplicas sem infraestrutura extra.
Quando a fila com Redis chegar (#96), basta outra implementação desta mesma interface.

Funcionamento ("reserva antes do trabalho caro", falha fechada):
1. `reservar` grava uma linha por regra e confirma (commit) ANTES do argon2;
2. conta a janela já incluindo a própria linha; se passou do limite, apaga a reserva e
   responde 429. Assim, uma rajada de requisições simultâneas não passa toda: no pior caso
   recusa a mais, nunca deixa passar a mais;
3. no login certo, `liberar` apaga a reserva e zera o contador daquele e-mail.
"""

import hashlib
import hmac
import ipaddress
import math
import random
import uuid
from dataclasses import dataclass
from datetime import timedelta
from http import HTTPStatus
from typing import ClassVar

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import Configuracoes
from app.core.erros import ErroDominio
from app.esquemas.autenticacao import normalizar_email
from app.modelos.tentativa import TentativaAcesso

CHANCE_LIMPEZA = 0.02  # ~1 em 50 requisições faz a faxina das linhas vencidas
LOTE_LIMPEZA = 500
JANELA_MAXIMA = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class Regra:
    escopo: str  # "email", "ip" ou "email_ip"
    limite: int
    janela: timedelta


REGRAS: dict[str, tuple[Regra, ...]] = {
    "login": (
        # Por e-mail + IP: o atacante esgota só a própria combinação, não a conta da vítima.
        Regra("email_ip", 5, timedelta(minutes=15)),
        # Por e-mail (de qualquer lugar): teto alto contra ataque distribuído a uma conta.
        Regra("email", 30, timedelta(minutes=15)),
        # Por IP: folga para CGNAT (muitos usuários de operadora móvel no mesmo IP).
        Regra("ip", 50, timedelta(minutes=15)),
    ),
    "cadastro": (Regra("ip", 10, timedelta(hours=1)),),
    # Pedidos que disparam e-mail: limite baixo por destinatário (evita usar o sistema para
    # inundar a caixa de alguém) e um teto por IP.
    "recuperacao_senha": (
        Regra("email", 3, timedelta(hours=1)),
        Regra("ip", 20, timedelta(hours=1)),
    ),
    # Chaveado pelo id do usuário (não pelo e-mail, que muda a cada troca).
    "verificacao_email": (Regra("email", 3, timedelta(hours=1)),),
    "troca_email": (Regra("email", 3, timedelta(hours=1)),),
}


class MuitasTentativas(ErroDominio):
    status = HTTPStatus.TOO_MANY_REQUESTS

    def __init__(self, segundos: int) -> None:
        super().__init__("Muitas tentativas seguidas. Aguarde um pouco e tente de novo.")
        self.segundos = max(1, segundos)

    def cabecalhos_resposta(self) -> dict[str, str]:
        return {"Retry-After": str(self.segundos)}


def normalizar_ip(ip: str) -> str:
    """IPv4 como está; IPv4 mapeado em IPv6 vira IPv4; IPv6 é agrupado pelo /64.

    Um cliente IPv6 costuma ter um /64 inteiro: sem agrupar, trocaria de endereço à vontade.
    """
    try:
        endereco = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if isinstance(endereco, ipaddress.IPv6Address):
        if endereco.ipv4_mapped:
            return str(endereco.ipv4_mapped)
        return str(ipaddress.ip_network(f"{endereco}/64", strict=False))
    return str(endereco)


def _normalizar_email(email: str) -> str:
    """Mesma normalização do login: variantes Unicode/punycode do e-mail somam no mesmo contador."""
    try:
        return normalizar_email(email)
    except ValueError:
        return email.strip().lower()


class LimitadorTentativas:
    regras: ClassVar[dict[str, tuple[Regra, ...]]] = REGRAS

    def __init__(self, sessao: Session, config: Configuracoes) -> None:
        self._sessao = sessao
        # Subchave própria: o HMAC dos contadores não reutiliza diretamente o segredo do JWT.
        self._segredo = hmac.new(
            config.jwt_segredo.get_secret_value().encode(), b"limite-tentativas:v1", hashlib.sha256
        ).digest()

    def _valores(self, email: str | None, ip: str | None) -> dict[str, str]:
        valores: dict[str, str] = {}
        if email:
            valores["email"] = _normalizar_email(email)
        if ip:
            valores["ip"] = normalizar_ip(ip)
        if email and ip:
            valores["email_ip"] = f"{valores['email']}|{valores['ip']}"
        return valores

    def _chave(self, escopo: str, valor: str) -> str:
        return hmac.new(self._segredo, f"{escopo}:{valor}".encode(), hashlib.sha256).hexdigest()

    def reservar(
        self, acao: str, email: str | None = None, ip: str | None = None
    ) -> list[uuid.UUID]:
        """Registra a tentativa e recusa (429) se alguma regra passou do limite."""
        valores = self._valores(email, ip)
        linhas = [
            TentativaAcesso(acao=acao, chave=self._chave(regra.escopo, valores[regra.escopo]))
            for regra in self.regras[acao]
            if regra.escopo in valores
        ]
        self._sessao.add_all(linhas)
        self._sessao.commit()  # também devolve a conexão ao pool antes do trabalho caro
        reserva = [linha.id for linha in linhas]
        for regra, linha in zip(
            (r for r in self.regras[acao] if r.escopo in valores), linhas, strict=True
        ):
            espera = self._espera_se_estourou(acao, linha.chave, regra)
            if espera is not None:
                self._apagar(reserva)
                raise MuitasTentativas(espera)
        if random.random() < CHANCE_LIMPEZA:  # noqa: S311 - não é uso criptográfico
            self.limpar()
        return reserva

    def _espera_se_estourou(self, acao: str, chave: str, regra: Regra) -> int | None:
        """Segundos até sobrar vaga, ou None se ainda cabe. Usa o relógio do banco."""
        inicio = func.now() - regra.janela
        filtro = (
            TentativaAcesso.acao == acao,
            TentativaAcesso.chave == chave,
            TentativaAcesso.momento > inicio,
        )
        contagem = self._sessao.scalar(select(func.count()).where(*filtro)) or 0
        if contagem <= regra.limite:
            return None
        # A vaga abre quando sair a (contagem - limite)-ésima tentativa mais antiga.
        segundos = self._sessao.scalar(
            select(func.extract("epoch", TentativaAcesso.momento + regra.janela - func.now()))
            .where(*filtro)
            .order_by(TentativaAcesso.momento)
            .offset(contagem - regra.limite - 1)
            .limit(1)
        )
        return math.ceil(segundos or 0)

    def liberar(self, reserva: list[uuid.UUID], email: str, ip: str | None = None) -> None:
        """Login certo: a tentativa não conta e as falhas desse e-mail (e desse e-mail+IP) somem.

        O contador do IP não é zerado: senão um atacante com conta própria o zeraria.
        """
        valores = self._valores(email, ip)
        chaves = [
            self._chave(escopo, valores[escopo])
            for escopo in ("email", "email_ip")
            if escopo in valores
        ]
        self._sessao.execute(
            delete(TentativaAcesso).where(
                TentativaAcesso.id.in_(reserva) | TentativaAcesso.chave.in_(chaves)
            )
        )
        self._sessao.commit()

    def _apagar(self, reserva: list[uuid.UUID]) -> None:
        self._sessao.execute(delete(TentativaAcesso).where(TentativaAcesso.id.in_(reserva)))
        self._sessao.commit()

    def limpar(self) -> int:
        """Apaga um lote de linhas vencidas, pulando as travadas (sem disputa entre requisições)."""
        vencidas = (
            select(TentativaAcesso.id)
            .where(TentativaAcesso.momento < func.now() - JANELA_MAXIMA)
            .limit(LOTE_LIMPEZA)
            .with_for_update(skip_locked=True)
        )
        resultado = self._sessao.execute(
            delete(TentativaAcesso).where(TentativaAcesso.id.in_(vencidas.scalar_subquery()))
        )
        self._sessao.commit()
        return int(getattr(resultado, "rowcount", 0) or 0)
