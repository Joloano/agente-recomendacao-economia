"""Senhas (argon2id) e tokens de acesso (JWT)."""

import threading
import unicodedata
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from http import HTTPStatus
from pathlib import Path
from typing import ClassVar

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Configuracoes
from app.core.erros import ErroDominio
from app.modelos.enums import Papel

TAMANHO_MINIMO_SENHA = 10
TAMANHO_MAXIMO_SENHA = 128
EMISSOR = "agente-economia"
PUBLICO = "agente-economia-api"

# Parâmetros padrão do argon2-cffi (argon2id, RFC 9106, perfil de baixa memória).
_hasher = PasswordHasher()
# No máximo 4 hashes argon2 simultâneos por processo (~256 MiB de pico), mesmo sob ataque.
_SEMAFORO_HASH = threading.BoundedSemaphore(4)
ESPERA_MAXIMA_HASH_S = 2.0


class ServidorOcupado(ErroDominio):
    """Fila do argon2 cheia: melhor responder 503 rápido do que prender a requisição."""

    status = HTTPStatus.SERVICE_UNAVAILABLE
    cabecalhos: ClassVar[Mapping[str, str] | None] = {"Retry-After": "2"}


@contextmanager
def _vaga_para_hash() -> Iterator[None]:
    if not _SEMAFORO_HASH.acquire(timeout=ESPERA_MAXIMA_HASH_S):
        raise ServidorOcupado("O servidor está ocupado. Tente de novo em instantes.")
    try:
        yield
    finally:
        _SEMAFORO_HASH.release()


# Hash de uma senha qualquer: usado quando o e-mail não existe, para o tempo de resposta
# não revelar quais e-mails estão cadastrados.
_HASH_FICTICIO = _hasher.hash("senha-ficticia-para-tempo-constante")


class SenhaFraca(ValueError):
    """A senha não atende à política mínima."""


def normalizar_senha(senha: str) -> str:
    """NFKC (NIST 800-63B): a mesma senha digitada em teclados diferentes vira o mesmo texto."""
    return unicodedata.normalize("NFKC", senha)


@cache
def _senhas_comuns() -> frozenset[str]:
    arquivo = Path(__file__).parent / "dados" / "senhas_comuns.txt"
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    return frozenset(linha.strip() for linha in linhas if linha and not linha.startswith("#"))


def validar_politica_senha(senha: str, email: str = "") -> None:
    """Política inspirada no NIST SP 800-63B: tamanho, sem regras de composição forçadas."""
    senha = normalizar_senha(senha)
    if any(unicodedata.category(c) == "Cc" for c in senha):
        raise SenhaFraca("A senha não pode ter caracteres de controle.")
    if len(senha) < TAMANHO_MINIMO_SENHA:
        raise SenhaFraca(f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.")
    if len(senha) > TAMANHO_MAXIMO_SENHA:
        raise SenhaFraca(f"A senha pode ter no máximo {TAMANHO_MAXIMO_SENHA} caracteres.")
    if len(set(senha)) < 4:  # noqa: PLR2004
        raise SenhaFraca("A senha é repetitiva demais.")
    if email and senha.lower() in {email.lower(), email.split("@", maxsplit=1)[0].lower()}:
        raise SenhaFraca("A senha não pode ser igual ao e-mail.")
    if senha.lower() in _senhas_comuns():
        raise SenhaFraca("Esta senha é muito comum. Escolha outra.")


def gerar_hash(senha: str) -> str:
    with _vaga_para_hash():
        return _hasher.hash(normalizar_senha(senha))


def verificar_senha(senha: str, senha_hash: str | None) -> bool:
    """Confere a senha; com `senha_hash=None` gasta o mesmo tempo e devolve False.

    Senhas absurdamente longas não chegam ao argon2 (não gastam CPU à toa), mas levam o
    mesmo tempo de uma verificação comum.
    """
    if len(senha) > TAMANHO_MAXIMO_SENHA * 4:
        senha, senha_hash = "x", None
    try:
        with _vaga_para_hash():
            resultado = _hasher.verify(senha_hash or _HASH_FICTICIO, normalizar_senha(senha))
        return resultado and senha_hash is not None
    except (VerificationError, InvalidHashError, UnicodeError):
        return False


def precisa_rehash(senha_hash: str) -> bool:
    """True quando os parâmetros do argon2 mudaram e o hash deve ser recalculado no login."""
    return _hasher.check_needs_rehash(senha_hash)


@dataclass(frozen=True, slots=True)
class DadosToken:
    usuario_id: uuid.UUID
    papel: Papel
    expira_em: datetime
    versao: int


class TokenInvalido(Exception):
    """Token ausente, expirado, adulterado ou de outro emissor."""


def criar_token_acesso(
    usuario_id: uuid.UUID,
    papel: Papel,
    config: Configuracoes,
    agora: datetime | None = None,
    versao: int = 0,
) -> tuple[str, datetime]:
    emitido = agora or datetime.now(UTC)
    expira = emitido + timedelta(minutes=config.jwt_expiracao_minutos)
    carga = {
        "sub": str(usuario_id),
        "papel": papel.value,
        "iat": emitido,
        "nbf": emitido,
        "exp": expira,
        "iss": EMISSOR,
        "aud": PUBLICO,
        "jti": uuid.uuid4().hex,
        "tipo": "acesso",
        # Versão das credenciais do usuário: muda na troca de senha ou de e-mail e derruba
        # os tokens antigos (comparação exata, sem depender do relógio das réplicas).
        "ver": versao,
    }
    token = jwt.encode(carga, config.jwt_segredo.get_secret_value(), config.jwt_algoritmo)
    return token, expira


def ler_token_acesso(token: str, config: Configuracoes) -> DadosToken:
    try:
        carga = jwt.decode(
            token,
            config.jwt_segredo.get_secret_value(),
            # Algoritmo fixo: impede o ataque de trocar o "alg" do cabeçalho (ex.: "none").
            algorithms=[config.jwt_algoritmo],
            audience=PUBLICO,
            issuer=EMISSOR,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
        if carga.get("tipo") != "acesso":
            raise TokenInvalido("tipo de token inesperado")
        return DadosToken(
            usuario_id=uuid.UUID(carga["sub"]),
            papel=Papel(carga["papel"]),
            expira_em=datetime.fromtimestamp(carga["exp"], UTC),
            versao=int(carga.get("ver", 0)),
        )
    except (jwt.PyJWTError, ValueError, KeyError) as erro:
        raise TokenInvalido(str(erro)) from erro
