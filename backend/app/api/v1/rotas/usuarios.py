import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status

from app.api.dependencias import AdminDep, ConfigDep, SessaoDep, UsuarioDep
from app.api.v1.rotas.conta import avisar, chave_usuario, enviar_verificacao
from app.core.seguranca import criar_token_acesso
from app.esquemas.autenticacao import Token, UsuarioSaida
from app.esquemas.paginacao import Pagina, ParametrosPagina, parametros_pagina
from app.esquemas.usuarios import (
    PerfilAtualizacao,
    TrocaSenha,
    UsuarioAtualizacaoAdmin,
    UsuarioCriacao,
)
from app.integracoes.email import ServicoEmail, obter_servico_email
from app.modelos import Papel
from app.servicos.limite import LimitadorTentativas
from app.servicos.usuarios import ServicoUsuarios

admin = APIRouter(prefix="/admin/usuarios", tags=["Admin: usuários"])
perfil = APIRouter(prefix="/usuarios/eu", tags=["Meu perfil"])

RESPOSTAS_ADMIN: dict[int | str, dict[str, Any]] = {
    401: {"description": "Não autenticado"},
    403: {"description": "Não é admin"},
}


# ---------- admin ----------
@admin.get("", response_model=Pagina[UsuarioSaida], responses=RESPOSTAS_ADMIN)
def listar_usuarios(
    _admin: AdminDep,
    sessao: SessaoDep,
    pagina: Annotated[ParametrosPagina, Depends(parametros_pagina)],
    busca: Annotated[
        str | None, Query(max_length=120, description="Parte do nome ou e-mail")
    ] = None,
    papel: Papel | None = None,
    ativo: bool | None = None,
) -> Pagina[UsuarioSaida]:
    itens, total = ServicoUsuarios(sessao).listar(pagina, busca, papel, ativo)
    return Pagina(
        itens=[UsuarioSaida.model_validate(u) for u in itens],
        total=total,
        pagina=pagina.pagina,
        tamanho=pagina.tamanho,
    )


@admin.post(
    "",
    response_model=UsuarioSaida,
    status_code=status.HTTP_201_CREATED,
    responses={**RESPOSTAS_ADMIN, 409: {"description": "E-mail já cadastrado"}},
)
def criar_usuario(dados: UsuarioCriacao, _admin: AdminDep, sessao: SessaoDep) -> UsuarioSaida:
    usuario = ServicoUsuarios(sessao).criar(dados.nome, dados.email, dados.senha, dados.papel)
    return UsuarioSaida.model_validate(usuario)


@admin.get("/{usuario_id}", response_model=UsuarioSaida, responses=RESPOSTAS_ADMIN)
def obter_usuario(usuario_id: uuid.UUID, _admin: AdminDep, sessao: SessaoDep) -> UsuarioSaida:
    return UsuarioSaida.model_validate(ServicoUsuarios(sessao).obter(usuario_id))


@admin.patch(
    "/{usuario_id}",
    response_model=UsuarioSaida,
    summary="Atualiza dados, papel (promover/rebaixar) ou situação (ativar/desativar)",
    responses={**RESPOSTAS_ADMIN, 409: {"description": "E-mail em uso ou último admin"}},
)
def atualizar_usuario(
    usuario_id: uuid.UUID, dados: UsuarioAtualizacaoAdmin, admin_atual: AdminDep, sessao: SessaoDep
) -> UsuarioSaida:
    usuario = ServicoUsuarios(sessao).atualizar(usuario_id, dados, admin_atual)
    return UsuarioSaida.model_validate(usuario)


@admin.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**RESPOSTAS_ADMIN, 409: {"description": "Último admin ou a própria conta"}},
)
def excluir_usuario(usuario_id: uuid.UUID, admin_atual: AdminDep, sessao: SessaoDep) -> Response:
    ServicoUsuarios(sessao).excluir(usuario_id, admin_atual)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- próprio perfil ----------
@perfil.get("", response_model=UsuarioSaida)
def meu_perfil(usuario: UsuarioDep) -> UsuarioSaida:
    return UsuarioSaida.model_validate(usuario)


@perfil.patch(
    "",
    response_model=UsuarioSaida,
    responses={
        401: {"description": "Senha atual incorreta (exigida para trocar o e-mail)"},
        409: {"description": "E-mail em uso"},
    },
)
def atualizar_meu_perfil(
    dados: PerfilAtualizacao,
    usuario: UsuarioDep,
    sessao: SessaoDep,
    config: ConfigDep,
    email: Annotated[ServicoEmail, Depends(obter_servico_email)],
    tarefas: BackgroundTasks,
) -> UsuarioSaida:
    if dados.email is not None and dados.email != usuario.email:
        LimitadorTentativas(sessao, config).reservar("troca_email", email=chave_usuario(usuario))
    pendente = ServicoUsuarios(sessao).atualizar_perfil(usuario, dados)
    if pendente:
        # O e-mail só muda quando o novo endereço confirmar; o atual é avisado do pedido.
        avisar(
            usuario, usuario.email, "Pedido de troca do e-mail da sua conta", config, email, tarefas
        )
        enviar_verificacao(usuario, pendente, sessao, config, email, tarefas)
    return UsuarioSaida.model_validate(usuario)


@perfil.post(
    "/senha",
    response_model=Token,
    summary="Troca a senha; derruba as outras sessões e devolve um token novo para esta",
    responses={401: {"description": "Senha atual incorreta"}, 422: {"description": "Senha fraca"}},
)
def trocar_minha_senha(
    dados: TrocaSenha,
    usuario: UsuarioDep,
    sessao: SessaoDep,
    config: ConfigDep,
    email: Annotated[ServicoEmail, Depends(obter_servico_email)],
    tarefas: BackgroundTasks,
) -> Token:
    ServicoUsuarios(sessao).trocar_senha(usuario, dados)
    avisar(usuario, usuario.email, "Sua senha foi alterada", config, email, tarefas)
    token, expira = criar_token_acesso(
        usuario.id, usuario.papel, config, versao=usuario.versao_credenciais
    )
    return Token(access_token=token, expira_em=expira)
