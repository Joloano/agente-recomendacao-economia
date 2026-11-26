from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agente import Essencialidade, Recurso, Resposta
from app.modelos import (
    Categoria,
    Equipamento,
    Feedback,
    Papel,
    Preferencia,
    Recomendacao,
    RecursoSimulacao,
    Residencia,
    Simulacao,
    StatusRecomendacao,
    Usuario,
)


def _usuario(email: str = "ana@exemplo.com") -> Usuario:
    return Usuario(nome="Ana", email=email, senha_hash="hash")


def _residencia(usuario: Usuario) -> Residencia:
    return Residencia(
        usuario=usuario,
        nome="Casa",
        numero_moradores=3,
        meta_energia_kwh_dia=Decimal("8.5"),
        meta_agua_litros_dia=Decimal(450),
        tarifa_energia_rs_kwh=Decimal("0.93"),
        tarifa_agua_rs_m3=Decimal("7.2"),
    )


def _equipamento(residencia: Residencia, categoria: Categoria, **mudancas: Any) -> Equipamento:
    dados: dict[str, Any] = {
        "residencia": residencia,
        "categoria": categoria,
        "nome": "TV",
        "recurso": Recurso.ENERGIA,
        "potencia_kw": Decimal("0.12"),
        "horas_uso_diario": Decimal(5),
        "consumo_diario_estimado": Decimal("0.6"),
        "reducao_uso": True,
        "essencialidade": Essencialidade.NAO_ESSENCIAL,
        "impacto_conforto_1a5": 2,
        "flexibilidade_1a5": 4,
        "esforco_1a5": 1,
        "economia_potencial": Decimal("0.2"),
    }
    return Equipamento(**{**dados, **mudancas})


@pytest.fixture
def categoria(sessao: Session) -> Categoria:
    categoria = Categoria(
        nome="entretenimento", recurso=Recurso.ENERGIA, descricao_acao="Desligar a TV."
    )
    sessao.add(categoria)
    sessao.flush()
    return categoria


def test_grafo_completo_e_persistido_com_valores_padrao(
    sessao: Session, categoria: Categoria
) -> None:
    residencia = _residencia(_usuario())
    residencia.preferencia = Preferencia(
        peso_economia=Decimal("0.4"),
        peso_conforto=Decimal("0.3"),
        peso_flexibilidade=Decimal("0.2"),
        peso_baixo_esforco=Decimal("0.1"),
    )
    equipamento = _equipamento(residencia, categoria)
    simulacao = Simulacao(residencia=residencia, recurso=RecursoSimulacao.ENERGIA)
    recomendacao = Recomendacao(
        simulacao=simulacao,
        equipamento=equipamento,
        nota_economia=Decimal(5),
        nota_conforto=Decimal(4),
        nota_flexibilidade=Decimal(4),
        nota_baixo_esforco=Decimal(5),
        utilidade=Decimal("4.4"),
        posicao=1,
    )
    recomendacao.feedback = Feedback(
        usuario=residencia.usuario,
        resposta=Resposta.ACEITAR,
        consumo_antes=Decimal("0.6"),
        consumo_depois=Decimal("0.4"),
    )
    sessao.add(residencia)
    sessao.flush()
    sessao.expire_all()

    salvo = sessao.scalars(select(Usuario)).one()
    assert salvo.papel is Papel.CLIENTE
    assert salvo.ativo
    assert salvo.criado_em is not None
    rec = salvo.residencias[0].simulacoes[0].recomendacoes[0]
    assert rec.status is StatusRecomendacao.PENDENTE
    assert rec.feedback is not None and rec.feedback.resposta is Resposta.ACEITAR
    assert rec.equipamento.essencialidade is Essencialidade.NAO_ESSENCIAL


@pytest.mark.parametrize(
    ("mudancas", "constraint"),
    [
        ({"impacto_conforto_1a5": 6}, "impacto_conforto_1a5_entre_1_e_5"),
        ({"esforco_1a5": 0}, "esforco_1a5_entre_1_e_5"),
        ({"horas_uso_diario": Decimal(25)}, "horas_no_maximo_24"),
        ({"economia_potencial": Decimal(-1)}, "valores_nao_negativos"),
        ({"potencia_kw": None}, "medida_conforme_recurso"),
        ({"recurso": Recurso.AGUA}, "medida_conforme_recurso"),
    ],
)
def test_banco_recusa_equipamento_invalido(
    sessao: Session, categoria: Categoria, mudancas: dict[str, Any], constraint: str
) -> None:
    sessao.add(_equipamento(_residencia(_usuario()), categoria, **mudancas))

    with pytest.raises(IntegrityError, match=constraint):
        sessao.flush()


def test_equipamento_de_agua_exige_vazao(sessao: Session, categoria: Categoria) -> None:
    agua = _equipamento(
        _residencia(_usuario()),
        categoria,
        recurso=Recurso.AGUA,
        potencia_kw=None,
        vazao_litros_min=Decimal(9),
    )
    sessao.add(agua)
    sessao.flush()

    assert agua.id is not None


def test_email_e_unico(sessao: Session) -> None:
    sessao.add_all([_usuario(), _usuario()])

    with pytest.raises(IntegrityError, match="uq_usuario_email"):
        sessao.flush()


def test_excluir_usuario_remove_residencias_e_equipamentos(
    sessao: Session, categoria: Categoria
) -> None:
    usuario = _usuario()
    _equipamento(_residencia(usuario), categoria)
    sessao.add(usuario)
    sessao.flush()

    sessao.delete(usuario)
    sessao.flush()

    assert sessao.scalars(select(Equipamento)).all() == []
    assert sessao.scalars(select(Categoria)).one() is categoria


def test_categoria_em_uso_nao_pode_ser_excluida(sessao: Session, categoria: Categoria) -> None:
    sessao.add(_equipamento(_residencia(_usuario()), categoria))
    sessao.flush()

    sessao.delete(categoria)
    with pytest.raises(IntegrityError):
        sessao.flush()
