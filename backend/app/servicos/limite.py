"""Limite de tentativas por janela deslizante, guardado no PostgreSQL (#137).

No banco (e não em memória) para valer entre workers e réplicas sem infraestrutura extra.
Quando a fila com Redis chegar (#96), basta outra implementação desta mesma interface.
"""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import ClassVar

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import Configuracoes
from app.core.erros import ErroDominio
from app.modelos.tentativa import TentativaAcesso


@dataclass(frozen=True, slots=True)
class Regra:
    escopo: str  # "email" ou "ip"
    limite: int
    janela: timedelta


REGRAS: dict[str, tuple[Regra, ...]] = {
    # Login: só falhas contam; um acerto zera o contador do e-mail.
    "login": (
        Regra("email", 5, timedelta(minutes=15)),
        Regra("ip", 20, timedelta(minutes=15)),
    ),
    "cadastro": (Regra("ip", 10, timedelta(hours=1)),),
}


class MuitasTentativas(ErroDominio):
    status = HTTPStatus.TOO_MANY_REQUESTS

    def __init__(self, segundos: int) -> None:
        super().__init__("Muitas tentativas seguidas. Aguarde um pouco e tente de novo.")
        self.segundos = max(1, segundos)

    def cabecalhos_resposta(self) -> dict[str, str]:
        return {"Retry-After": str(self.segundos)}


class LimitadorTentativas:
    regras: ClassVar[dict[str, tuple[Regra, ...]]] = REGRAS

    def __init__(self, sessao: Session, config: Configuracoes) -> None:
        self._sessao = sessao
        self._segredo = config.jwt_segredo.get_secret_value().encode()

    def _chave(self, escopo: str, valor: str) -> str:
        mensagem = f"{escopo}:{valor.strip().lower()}".encode()
        return hmac.new(self._segredo, mensagem, hashlib.sha256).hexdigest()

    def verificar(self, acao: str, valores: dict[str, str]) -> None:
        """Levanta MuitasTentativas se alguma regra da ação estourou o limite."""
        agora = datetime.now(UTC)
        for regra in self.regras[acao]:
            valor = valores.get(regra.escopo)
            if not valor:
                continue
            desde = agora - regra.janela
            contagem, mais_antiga = self._sessao.execute(
                select(func.count(), func.min(TentativaAcesso.momento)).where(
                    TentativaAcesso.acao == acao,
                    TentativaAcesso.chave == self._chave(regra.escopo, valor),
                    TentativaAcesso.momento > desde,
                )
            ).one()
            if contagem >= regra.limite:
                restante = (mais_antiga + regra.janela - agora).total_seconds()
                raise MuitasTentativas(int(restante) + 1)

    def registrar(self, acao: str, valores: dict[str, str]) -> None:
        regras = self.regras[acao]
        for regra in regras:
            if valor := valores.get(regra.escopo):
                self._sessao.add(TentativaAcesso(acao=acao, chave=self._chave(regra.escopo, valor)))
        # Limpeza: nada precisa sobreviver além da maior janela da ação.
        maior_janela = max(regra.janela for regra in regras)
        self._sessao.execute(
            delete(TentativaAcesso).where(
                TentativaAcesso.acao == acao,
                TentativaAcesso.momento < datetime.now(UTC) - maior_janela,
            )
        )
        self._sessao.commit()

    def zerar(self, acao: str, escopo: str, valor: str) -> None:
        self._sessao.execute(
            delete(TentativaAcesso).where(
                TentativaAcesso.acao == acao, TentativaAcesso.chave == self._chave(escopo, valor)
            )
        )
        self._sessao.commit()
