from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Ambiente, Configuracoes

SEGREDO_FORTE = "x" * 48


def _config(**valores: Any) -> Configuracoes:
    return Configuracoes(_env_file=None, **valores)


def test_dev_aceita_valores_padrao() -> None:
    config = _config(ambiente=Ambiente.DEV)

    assert not config.eh_producao
    assert config.url_banco.startswith("postgresql+psycopg://agente:")


@pytest.mark.parametrize("ambiente", [Ambiente.STAGING, Ambiente.PRODUCAO])
def test_producao_recusa_segredos_padrao(ambiente: Ambiente) -> None:
    with pytest.raises(ValidationError, match="POSTGRES_SENHA, JWT_SEGREDO, ADMIN_SENHA"):
        _config(ambiente=ambiente)


def test_producao_recusa_segredo_jwt_curto() -> None:
    with pytest.raises(ValidationError, match="pelo menos 32"):
        _config(
            ambiente=Ambiente.PRODUCAO,
            postgres_senha="senha-boa",
            admin_senha="senha-boa",
            jwt_segredo="curto",
        )


def test_producao_aceita_segredos_fortes() -> None:
    config = _config(
        ambiente=Ambiente.PRODUCAO,
        postgres_senha="senha-boa",
        admin_senha="senha-boa",
        jwt_segredo=SEGREDO_FORTE,
    )

    assert config.eh_producao


def test_le_variaveis_de_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "banco-externo")
    monkeypatch.setenv("CORS_ORIGENS", '["https://app.exemplo.com"]')

    config = _config()

    assert config.postgres_host == "banco-externo"
    assert config.cors_origens == ["https://app.exemplo.com"]


def test_env_example_contem_todas_as_configuracoes() -> None:
    exemplo = (Path(__file__).parents[2] / ".env.example").read_text(encoding="utf-8")
    for campo in Configuracoes.model_fields:
        assert f"{campo.upper()}=" in exemplo, f"{campo.upper()} faltando no .env.example"
