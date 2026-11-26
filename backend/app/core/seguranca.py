"""Senhas (argon2id) e tokens de acesso (JWT)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Configuracoes
from app.modelos.enums import Papel

TAMANHO_MINIMO_SENHA = 10
TAMANHO_MAXIMO_SENHA = 128
EMISSOR = "agente-economia"
PUBLICO = "agente-economia-api"

# Parâmetros padrão do argon2-cffi (argon2id, RFC 9106, perfil de baixa memória).
_hasher = PasswordHasher()
# Hash de uma senha qualquer: usado quando o e-mail não existe, para o tempo de resposta
# não revelar quais e-mails estão cadastrados.
_HASH_FICTICIO = _hasher.hash("senha-ficticia-para-tempo-constante")


class SenhaFraca(ValueError):
    """A senha não atende à política mínima."""


def validar_politica_senha(senha: str, email: str = "") -> None:
    """Política inspirada no NIST SP 800-63B: tamanho, sem regras de composição forçadas."""
    if len(senha) < TAMANHO_MINIMO_SENHA:
        raise SenhaFraca(f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.")
    if len(senha) > TAMANHO_MAXIMO_SENHA:
        raise SenhaFraca(f"A senha pode ter no máximo {TAMANHO_MAXIMO_SENHA} caracteres.")
    if len(set(senha)) < 4:  # noqa: PLR2004
        raise SenhaFraca("A senha é repetitiva demais.")
    if email and senha.lower() in {email.lower(), email.split("@", maxsplit=1)[0].lower()}:
        raise SenhaFraca("A senha não pode ser igual ao e-mail.")


def gerar_hash(senha: str) -> str:
    return _hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str | None) -> bool:
    """Confere a senha; com `senha_hash=None` gasta o mesmo tempo e devolve False."""
    try:
        return _hasher.verify(senha_hash or _HASH_FICTICIO, senha) and senha_hash is not None
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


class TokenInvalido(Exception):
    """Token ausente, expirado, adulterado ou de outro emissor."""


def criar_token_acesso(
    usuario_id: uuid.UUID, papel: Papel, config: Configuracoes, agora: datetime | None = None
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
        )
    except (jwt.PyJWTError, ValueError, KeyError) as erro:
        raise TokenInvalido(str(erro)) from erro
