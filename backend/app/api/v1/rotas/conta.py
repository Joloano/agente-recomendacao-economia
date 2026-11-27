"""Verificação de e-mail e recuperação de senha (#90).

Os e-mails saem em segundo plano (BackgroundTasks): a resposta não espera o servidor de
e-mail, e uma falha de envio não desfaz a operação.
"""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status
from sqlalchemy import select

from app.api.dependencias import ConfigDep, SessaoDep, UsuarioDep
from app.core.config import Configuracoes
from app.esquemas.autenticacao import (
    ConfirmacaoToken,
    PedidoRecuperacao,
    RedefinicaoSenha,
    UsuarioSaida,
)
from app.integracoes.email import ServicoEmail, obter_servico_email
from app.modelos import FinalidadeToken, Usuario
from app.servicos.limite import LimitadorTentativas
from app.servicos.tokens_conta import VALIDADE, ServicoTokensConta, TokenContaInvalido
from app.servicos.usuarios import ServicoUsuarios, validar_senha

router = APIRouter(prefix="/auth", tags=["Conta: verificação e recuperação"])

EmailDep = Annotated[ServicoEmail, Depends(obter_servico_email)]
RESPOSTAS: dict[int | str, dict[str, Any]] = {
    429: {"description": "Muitas tentativas; veja o cabeçalho Retry-After"},
}


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


def enviar_verificacao(
    usuario: Usuario,
    sessao: SessaoDep,
    config: Configuracoes,
    email: ServicoEmail,
    tarefas: BackgroundTasks,
) -> None:
    """Emite o token e agenda o e-mail de verificação (usado também no cadastro)."""
    token = ServicoTokensConta(sessao).emitir(usuario, FinalidadeToken.VERIFICACAO_EMAIL)
    horas = int(VALIDADE[FinalidadeToken.VERIFICACAO_EMAIL].total_seconds() // 3600)
    mensagem = email.verificacao(
        usuario.email, usuario.nome, f"{config.url_frontend}/verificar-email?token={token}", horas
    )
    tarefas.add_task(email.enviar, mensagem)


@router.post(
    "/verificacao/solicitar",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Envia (de novo) o e-mail de confirmação para o usuário autenticado",
    responses=RESPOSTAS,
)
def solicitar_verificacao(
    usuario: UsuarioDep,
    sessao: SessaoDep,
    config: ConfigDep,
    email: EmailDep,
    tarefas: BackgroundTasks,
) -> Response:
    if usuario.email_verificado_em is None:
        LimitadorTentativas(sessao, config).reservar("verificacao_email", email=usuario.email)
        enviar_verificacao(usuario, sessao, config, email, tarefas)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post(
    "/verificacao/confirmar",
    response_model=UsuarioSaida,
    summary="Confirma o e-mail com o token recebido no link",
    responses={422: {"description": "Link inválido ou expirado"}},
)
def confirmar_verificacao(dados: ConfirmacaoToken, sessao: SessaoDep) -> UsuarioSaida:
    usuario, registro = ServicoTokensConta(sessao).consumir(
        dados.token, FinalidadeToken.VERIFICACAO_EMAIL
    )
    # O link confirma o endereço para o qual foi enviado: se o e-mail mudou depois, não vale.
    if registro.email_alvo != usuario.email:
        sessao.rollback()
        raise TokenContaInvalido("Este link é inválido ou expirou. Peça um novo.")
    usuario.email_verificado_em = datetime.now(UTC)
    sessao.commit()
    return UsuarioSaida.model_validate(usuario)


@router.post(
    "/senha/esqueci",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Envia o link de redefinição de senha, se o e-mail tiver conta",
    responses=RESPOSTAS,
)
def esqueci_senha(
    dados: PedidoRecuperacao,
    request: Request,
    sessao: SessaoDep,
    config: ConfigDep,
    email: EmailDep,
    tarefas: BackgroundTasks,
) -> Response:
    """Sempre 202: a resposta nunca revela se o e-mail está cadastrado."""
    LimitadorTentativas(sessao, config).reservar(
        "recuperacao_senha", email=dados.email, ip=_ip(request)
    )
    usuario = sessao.scalars(select(Usuario).where(Usuario.email == dados.email)).one_or_none()
    if usuario is not None and usuario.ativo:
        token = ServicoTokensConta(sessao).emitir(usuario, FinalidadeToken.RECUPERACAO_SENHA)
        minutos = int(VALIDADE[FinalidadeToken.RECUPERACAO_SENHA].total_seconds() // 60)
        mensagem = email.recuperacao_senha(
            usuario.email,
            usuario.nome,
            f"{config.url_frontend}/redefinir-senha?token={token}",
            minutos,
        )
        tarefas.add_task(email.enviar, mensagem)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post(
    "/senha/redefinir",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Define uma nova senha com o token do link (derruba as sessões abertas)",
    responses={422: {"description": "Link inválido ou expirado, ou senha fraca"}},
)
def redefinir_senha(dados: RedefinicaoSenha, sessao: SessaoDep) -> Response:
    servico_tokens = ServicoTokensConta(sessao)
    # A senha é validada antes de consumir o link: senha fraca não gasta o link.
    validar_senha(
        dados.nova_senha, servico_tokens.dono(dados.token, FinalidadeToken.RECUPERACAO_SENHA).email
    )
    usuario, _registro = servico_tokens.consumir(dados.token, FinalidadeToken.RECUPERACAO_SENHA)
    # Quem recebeu o link no e-mail provou que controla o endereço.
    usuario.email_verificado_em = usuario.email_verificado_em or datetime.now(UTC)
    ServicoUsuarios(sessao).definir_senha(usuario, dados.nova_senha)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
