import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencias import AdminDep, SessaoDep, UsuarioDep
from app.esquemas.autenticacao import UsuarioSaida
from app.esquemas.paginacao import Pagina, ParametrosPagina, parametros_pagina
from app.esquemas.usuarios import (
    PerfilAtualizacao,
    TrocaSenha,
    UsuarioAtualizacaoAdmin,
    UsuarioCriacao,
)
from app.modelos import Papel
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
    dados: PerfilAtualizacao, usuario: UsuarioDep, sessao: SessaoDep
) -> UsuarioSaida:
    return UsuarioSaida.model_validate(ServicoUsuarios(sessao).atualizar_perfil(usuario, dados))


@perfil.post(
    "/senha",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"description": "Senha atual incorreta"}, 422: {"description": "Senha fraca"}},
)
def trocar_minha_senha(dados: TrocaSenha, usuario: UsuarioDep, sessao: SessaoDep) -> Response:
    ServicoUsuarios(sessao).trocar_senha(usuario, dados)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
