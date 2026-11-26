from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Ambiente, Configuracoes

ENV_EXAMPLE = Path(__file__).parents[2] / ".env.example"
PRODUCAO_VALIDA: dict[str, Any] = {
    "ambiente": Ambiente.PRODUCAO,
    "postgres_host": "db",
    "postgres_db": "agente",
    "postgres_usuario": "agente",
    "postgres_senha": "Senha-Do-Banco-Forte!",
    "jwt_segredo": "x" * 48,
    "admin_email": "admin@empresa.com.br",
    "admin_senha": "Senha-Do-Admin-Forte!",
    "cors_origens": "https://app.empresa.com.br",
    "url_frontend": "https://app.empresa.com.br",
}


def _config(**valores: Any) -> Configuracoes:
    return Configuracoes(_env_file=None, **valores)


def test_dev_aceita_valores_padrao() -> None:
    config = _config(ambiente=Ambiente.DEV)

    assert not config.eh_producao
    assert config.url_banco.drivername == "postgresql+psycopg"


def test_env_example_e_valido_e_completo() -> None:
    config = Configuracoes(_env_file=ENV_EXAMPLE)
    exemplo = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert config.cors_origens == ["http://localhost:4200"]
    for campo in Configuracoes.model_fields:
        assert f"{campo.upper()}=" in exemplo, f"{campo.upper()} faltando no .env.example"


def test_cors_aceita_lista_separada_por_virgula(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGENS", "https://a.com, https://b.com")

    assert _config().cors_origens == ["https://a.com", "https://b.com"]


def test_cors_nunca_aceita_curinga() -> None:
    with pytest.raises(ValidationError, match=r"não pode conter '\*'"):
        _config(cors_origens="*")


def test_senha_com_caracteres_especiais_e_escapada_na_url() -> None:
    url = _config(postgres_senha="p@ss/w:rd#1", postgres_host="db").url_banco

    assert url.host == "db"
    assert url.password == "p@ss/w:rd#1"
    assert "p@ss" not in repr(url)


def test_producao_aceita_configuracao_completa_e_forte() -> None:
    assert _config(**PRODUCAO_VALIDA).eh_producao


@pytest.mark.parametrize("ambiente", [Ambiente.STAGING, Ambiente.PRODUCAO])
def test_producao_exige_variaveis_explicitas(ambiente: Ambiente) -> None:
    with pytest.raises(ValidationError, match="defina POSTGRES_HOST"):
        _config(ambiente=ambiente)


@pytest.mark.parametrize(
    ("campo", "valor", "mensagem"),
    [
        ("postgres_senha", "curta", "POSTGRES_SENHA precisa"),
        ("admin_senha", "troque-esta-senha-forte", "ADMIN_SENHA precisa"),
        ("jwt_segredo", "segredo-curto", "JWT_SEGREDO precisa"),
        ("cors_origens", "http://localhost:4200", "não pode apontar para http://localhost:4200"),
    ],
)
def test_producao_recusa_valores_fracos(campo: str, valor: str, mensagem: str) -> None:
    with pytest.raises(ValidationError, match=mensagem):
        _config(**{**PRODUCAO_VALIDA, campo: valor})
