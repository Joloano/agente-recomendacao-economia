from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select, text
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
    StatusSimulacao,
    Usuario,
)


# ---------- construtores ----------
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


def _simulacao(residencia: Residencia, **mudancas: Any) -> Simulacao:
    dados: dict[str, Any] = {
        "residencia": residencia,
        "recurso": RecursoSimulacao.ENERGIA,
        "consumo_inicial_energia": Decimal("0.6"),
        "consumo_estimado_energia": Decimal("0.6"),
    }
    return Simulacao(**{**dados, **mudancas})


def _recomendacao(simulacao: Simulacao, equipamento: Equipamento, posicao: int = 1) -> Recomendacao:
    return Recomendacao(
        simulacao=simulacao,
        equipamento=equipamento,
        nota_economia=Decimal(5),
        nota_conforto=Decimal(4),
        nota_flexibilidade=Decimal(4),
        nota_baixo_esforco=Decimal(5),
        utilidade=Decimal("4.4"),
        posicao=posicao,
    )


@pytest.fixture
def categoria(sessao: Session) -> Categoria:
    categoria = Categoria(
        nome="entretenimento", recurso=Recurso.ENERGIA, descricao_acao="Desligar a TV."
    )
    sessao.add(categoria)
    sessao.flush()
    return categoria


@pytest.fixture
def cenario(sessao: Session, categoria: Categoria) -> Recomendacao:
    """Usuário → residência → equipamento → simulação → recomendação, já gravados."""
    residencia = _residencia(_usuario())
    recomendacao = _recomendacao(_simulacao(residencia), _equipamento(residencia, categoria))
    sessao.add(recomendacao)
    sessao.flush()
    return recomendacao


def _falha(sessao: Session, constraint: str) -> None:
    with pytest.raises(IntegrityError, match=constraint):
        sessao.flush()


# ---------- persistência e padrões ----------
def test_grafo_completo_e_persistido_com_valores_padrao(
    sessao: Session, cenario: Recomendacao
) -> None:
    residencia = cenario.simulacao.residencia
    residencia.preferencia = Preferencia(
        peso_economia=Decimal("0.4"),
        peso_conforto=Decimal("0.3"),
        peso_flexibilidade=Decimal("0.2"),
        peso_baixo_esforco=Decimal("0.1"),
    )
    cenario.feedback = Feedback(
        usuario=residencia.usuario,
        resposta=Resposta.ACEITAR,
        consumo_antes=Decimal("0.6"),
        consumo_depois=Decimal("0.4"),
    )
    sessao.flush()
    sessao.expire_all()

    salvo = sessao.scalars(select(Usuario)).one()
    assert salvo.papel is Papel.CLIENTE and salvo.ativo and salvo.criado_em is not None
    rec = salvo.residencias[0].simulacoes[0].recomendacoes[0]
    assert rec.residencia_id == salvo.residencias[0].id
    assert rec.status is StatusRecomendacao.PENDENTE
    assert rec.feedback is not None and rec.feedback.resposta is Resposta.ACEITAR


def test_valores_padrao_tambem_valem_para_sql_puro(sessao: Session) -> None:
    sessao.execute(
        text(
            "INSERT INTO usuario (id, nome, email, senha_hash) "
            "VALUES (gen_random_uuid(), 'Bia', 'bia@exemplo.com', 'h')"
        )
    )

    papel, ativo = sessao.execute(text("SELECT papel, ativo FROM usuario")).one()
    assert (papel, ativo) == ("cliente", True)


def test_atualizado_em_avanca_ao_alterar(sessao: Session, cenario: Recomendacao) -> None:
    usuario = cenario.simulacao.residencia.usuario
    antes = usuario.atualizado_em

    usuario.nome = "Ana Maria"
    sessao.flush()
    sessao.refresh(usuario)

    assert usuario.atualizado_em > antes


# ---------- constraints de equipamento ----------
@pytest.mark.parametrize(
    ("mudancas", "constraint"),
    [
        ({"impacto_conforto_1a5": 6}, "impacto_conforto_1a5_entre_1_e_5"),
        ({"esforco_1a5": 0}, "esforco_1a5_entre_1_e_5"),
        ({"horas_uso_diario": Decimal(25)}, "horas_no_maximo_24"),
        ({"economia_potencial": Decimal(-1)}, "valores_nao_negativos"),
        ({"potencia_kw": None}, "medida_conforme_recurso"),
    ],
)
def test_banco_recusa_equipamento_invalido(
    sessao: Session, categoria: Categoria, mudancas: dict[str, Any], constraint: str
) -> None:
    sessao.add(_equipamento(_residencia(_usuario()), categoria, **mudancas))
    _falha(sessao, constraint)


def test_equipamento_de_agua_exige_vazao_e_categoria_de_agua(sessao: Session) -> None:
    banho = Categoria(nome="banho", recurso=Recurso.AGUA, descricao_acao="Banhos curtos.")
    agua = _equipamento(
        _residencia(_usuario()),
        banho,
        recurso=Recurso.AGUA,
        potencia_kw=None,
        vazao_litros_min=Decimal(9),
    )
    sessao.add(agua)
    sessao.flush()

    assert agua.id is not None


def test_categoria_precisa_ser_do_mesmo_recurso(sessao: Session, categoria: Categoria) -> None:
    sessao.add(
        _equipamento(
            _residencia(_usuario()),
            categoria,  # categoria de energia
            recurso=Recurso.AGUA,
            potencia_kw=None,
            vazao_litros_min=Decimal(9),
        )
    )
    _falha(sessao, "fk_equipamento_categoria_mesmo_recurso")


# ---------- usuário ----------
def test_email_e_unico_e_em_minusculas(sessao: Session) -> None:
    sessao.add(_usuario("Ana@Exemplo.com"))
    _falha(sessao, "email_minusculo")


def test_email_duplicado_e_recusado(sessao: Session) -> None:
    sessao.add_all([_usuario(), _usuario()])
    _falha(sessao, "uq_usuario_email")


# ---------- simulação e recomendação ----------
@pytest.mark.parametrize(
    ("mudancas", "constraint"),
    [
        ({"consumo_inicial_energia": None}, "consumo_conforme_recurso"),
        ({"consumo_inicial_agua": Decimal(1)}, "consumo_conforme_recurso"),
        ({"consumo_estimado_energia": Decimal(-1)}, "consumo_nao_negativo"),
        ({"status": StatusSimulacao.ENCERRADA}, "encerramento_coerente"),
        ({"encerrada_em": datetime.now(UTC)}, "encerramento_coerente"),
    ],
)
def test_banco_recusa_simulacao_incoerente(
    sessao: Session, mudancas: dict[str, Any], constraint: str
) -> None:
    sessao.add(_simulacao(_residencia(_usuario()), **mudancas))
    _falha(sessao, constraint)


def test_so_uma_simulacao_ativa_por_residencia(sessao: Session, cenario: Recomendacao) -> None:
    residencia = cenario.simulacao.residencia
    encerrada = _simulacao(
        residencia, status=StatusSimulacao.ENCERRADA, encerrada_em=datetime.now(UTC)
    )
    sessao.add(encerrada)
    sessao.flush()

    sessao.add(_simulacao(residencia))
    _falha(sessao, "uq_simulacao_uma_ativa_por_residencia")


def test_recomendacao_nao_mistura_residencias(
    sessao: Session, cenario: Recomendacao, categoria: Categoria
) -> None:
    equipamento_alheio = _equipamento(_residencia(_usuario("bia@exemplo.com")), categoria)
    sessao.add(_recomendacao(cenario.simulacao, equipamento_alheio, posicao=2))
    sessao.flush()

    with pytest.raises(IntegrityError, match="fk_recomendacao_equipamento_mesma_residencia"):
        sessao.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_posicoes_podem_ser_trocadas_na_mesma_transacao(
    sessao: Session, cenario: Recomendacao, categoria: Categoria
) -> None:
    outra = _recomendacao(
        cenario.simulacao, _equipamento(cenario.simulacao.residencia, categoria), posicao=2
    )
    sessao.add(outra)
    sessao.flush()

    cenario.posicao, outra.posicao = 2, 1
    sessao.flush()
    sessao.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    assert (cenario.posicao, outra.posicao) == (2, 1)


def test_posicao_repetida_e_recusada_ao_confirmar(
    sessao: Session, cenario: Recomendacao, categoria: Categoria
) -> None:
    sessao.add(
        _recomendacao(
            cenario.simulacao, _equipamento(cenario.simulacao.residencia, categoria), posicao=1
        )
    )
    sessao.flush()

    with pytest.raises(IntegrityError, match="uq_recomendacao_posicao"):
        sessao.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


# ---------- exclusões ----------
def test_equipamento_com_recomendacao_nao_pode_ser_apagado(
    sessao: Session, cenario: Recomendacao
) -> None:
    sessao.delete(cenario.equipamento)
    sessao.flush()

    with pytest.raises(IntegrityError, match="fk_recomendacao_equipamento_mesma_residencia"):
        sessao.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


@pytest.mark.parametrize("tabela", ["usuario", "residencia"])
def test_exclusao_pelo_banco_apaga_todo_o_historico(
    sessao: Session, cenario: Recomendacao, categoria: Categoria, tabela: str
) -> None:
    """DELETE em SQL puro, sem nada na sessão: prova a cascata do banco, não a do ORM."""
    residencia = cenario.simulacao.residencia
    alvo = residencia.usuario_id if tabela == "usuario" else residencia.id
    sessao.expunge_all()

    sessao.execute(text(f"DELETE FROM {tabela} WHERE id = :id"), {"id": alvo})  # noqa: S608
    sessao.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    for modelo in (Residencia, Equipamento, Simulacao, Recomendacao):
        assert sessao.scalars(select(modelo)).all() == []
    assert sessao.scalars(select(Categoria)).one().id == categoria.id


def test_exclusao_pelo_orm_sem_filhos_carregados(sessao: Session, cenario: Recomendacao) -> None:
    usuario_id = cenario.simulacao.residencia.usuario_id
    sessao.expunge_all()

    sessao.delete(sessao.get_one(Usuario, usuario_id))
    sessao.flush()
    sessao.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

    assert sessao.scalars(select(Recomendacao)).all() == []


def test_excluir_quem_respondeu_mantem_o_feedback(sessao: Session, cenario: Recomendacao) -> None:
    membro = _usuario("membro@exemplo.com")
    cenario.feedback = Feedback(
        usuario=membro,
        resposta=Resposta.REJEITAR,
        consumo_antes=Decimal("0.6"),
        consumo_depois=Decimal("0.6"),
    )
    sessao.flush()

    sessao.delete(membro)
    sessao.flush()
    sessao.expire_all()

    feedback = sessao.scalars(select(Feedback)).one()
    assert feedback.usuario_id is None


def test_categoria_em_uso_nao_pode_ser_excluida(sessao: Session, cenario: Recomendacao) -> None:
    sessao.delete(cenario.equipamento.categoria)
    with pytest.raises(IntegrityError):
        sessao.flush()
