import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import Configuracoes
from app.core.seguranca import (
    EMISSOR,
    PUBLICO,
    SenhaFraca,
    TokenInvalido,
    criar_token_acesso,
    gerar_hash,
    ler_token_acesso,
    precisa_rehash,
    validar_politica_senha,
    verificar_senha,
)
from app.modelos import Papel

CONFIG = Configuracoes(_env_file=None, jwt_segredo="s" * 48)
ID = uuid.uuid4()


# ---------- senhas ----------
@pytest.mark.parametrize(
    ("senha", "mensagem"),
    [
        ("curta123", "pelo menos 10"),
        ("a" * 129, "no máximo 128"),
        ("abababababab", "repetitiva"),
        ("ana.souza@exemplo.com", "igual ao e-mail"),
        ("ANA.SOUZA1", "igual ao e-mail"),
    ],
)
def test_politica_recusa_senhas_fracas(senha: str, mensagem: str) -> None:
    email = "ana.souza1@exemplo.com" if senha == "ANA.SOUZA1" else "ana.souza@exemplo.com"
    with pytest.raises(SenhaFraca, match=mensagem):
        validar_politica_senha(senha, email)


def test_politica_aceita_frase_longa_sem_regras_de_composicao() -> None:
    validar_politica_senha("cavalo bateria grampo correto", "ana@exemplo.com")


def test_hash_argon2id_confere_e_nao_guarda_a_senha() -> None:
    senha_hash = gerar_hash("uma senha bem longa")

    assert senha_hash.startswith("$argon2id$")
    assert "uma senha" not in senha_hash
    assert verificar_senha("uma senha bem longa", senha_hash)
    assert not verificar_senha("outra senha qualquer", senha_hash)
    assert not precisa_rehash(senha_hash)


def test_verificar_sem_hash_ou_com_hash_corrompido_e_falso() -> None:
    assert not verificar_senha("qualquer", None)
    assert not verificar_senha("qualquer", "não-é-um-hash")


# ---------- tokens ----------
def test_token_ida_e_volta() -> None:
    token, expira = criar_token_acesso(ID, Papel.ADMIN, CONFIG)

    dados = ler_token_acesso(token, CONFIG)

    assert dados.usuario_id == ID
    assert dados.papel is Papel.ADMIN
    assert dados.expira_em == expira.replace(microsecond=0)


def test_token_expirado_e_recusado() -> None:
    passado = datetime.now(UTC) - timedelta(hours=2)
    token, _ = criar_token_acesso(ID, Papel.CLIENTE, CONFIG, agora=passado)

    with pytest.raises(TokenInvalido, match="expired"):
        ler_token_acesso(token, CONFIG)


def _assinar(carga: dict[str, object], segredo: str = "s" * 48, alg: str = "HS256") -> str:
    base: dict[str, object] = {
        "sub": str(ID),
        "papel": "admin",
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iss": EMISSOR,
        "aud": PUBLICO,
        "tipo": "acesso",
    }
    return jwt.encode({**base, **carga}, segredo, algorithm=alg)


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(_assinar({}, segredo="outro-segredo-" * 4), id="assinatura-de-outro-segredo"),
        pytest.param(_assinar({"aud": "outra-api"}), id="outro-publico"),
        pytest.param(_assinar({"iss": "outro-emissor"}), id="outro-emissor"),
        pytest.param(_assinar({"tipo": "renovacao"}), id="tipo-errado"),
        pytest.param(_assinar({"papel": "superusuario"}), id="papel-inexistente"),
        pytest.param(_assinar({"sub": "nao-e-uuid"}), id="sub-invalido"),
        pytest.param(
            jwt.encode({"sub": str(ID)}, None, algorithm="none"),
            id="alg-none",
        ),
        pytest.param("lixo", id="malformado"),
    ],
)
def test_tokens_adulterados_sao_recusados(token: str) -> None:
    with pytest.raises(TokenInvalido):
        ler_token_acesso(token, CONFIG)


def test_token_sem_expiracao_e_recusado() -> None:
    token = jwt.encode(
        {"sub": str(ID), "papel": "admin", "iat": datetime.now(UTC), "iss": EMISSOR,
         "aud": PUBLICO, "tipo": "acesso"},
        "s" * 48,
        algorithm="HS256",
    )  # fmt: skip

    with pytest.raises(TokenInvalido, match="exp"):
        ler_token_acesso(token, CONFIG)
