"""Verificação de e-mail, troca de e-mail e recuperação de senha (#90).

- Os links levam o token no fragmento (`#token=`): o navegador nunca o envia ao servidor, então
  ele não aparece em logs nem no cabeçalho Referer.
- Os e-mails saem em segundo plano (BackgroundTasks); uma falha de envio não desfaz a operação.
"""

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status
from sqlalchemy import select

from app.api.dependencias import ConfigDep, SessaoDep, UsuarioDep
from app.core.banco import FabricaSessao, obter_fabrica_sessao
from app.core.config import Configuracoes
from app.core.erros import Conflito
from app.esquemas.autenticacao import (
    ConfirmacaoToken,
    PedidoRecuperacao,
    RedefinicaoSenha,
    UsuarioSaida,
)
from app.integracoes.email import ServicoEmail, obter_servico_email
from app.modelos import FinalidadeToken, Usuario
from app.servicos.limite import LimitadorTentativas
from app.servicos.tokens_conta import (
    MENSAGEM_INVALIDO,
    VALIDADE,
    ServicoTokensConta,
    TokenContaInvalido,
)
from app.servicos.usuarios import ServicoUsuarios, validar_senha

router = APIRouter(prefix="/auth", tags=["Conta: verificação e recuperação"])

EmailDep = Annotated[ServicoEmail, Depends(obter_servico_email)]
FabricaDep = Annotated[FabricaSessao, Depends(obter_fabrica_sessao)]
RESPOSTAS: dict[int | str, dict[str, Any]] = {
    429: {"description": "Muitas tentativas; veja o cabeçalho Retry-After"},
}


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


def chave_usuario(usuario: Usuario) -> str:
    """Chave de limite pelo id: não muda quando o e-mail muda."""
    return f"usuario:{usuario.id}"


def enviar_verificacao(
    usuario: Usuario,
    destino: str,
    sessao: SessaoDep,
    config: Configuracoes,
    email: ServicoEmail,
    tarefas: BackgroundTasks,
) -> None:
    """Emite um token preso a `destino` e agenda o e-mail de confirmação para ele."""
    token = ServicoTokensConta(sessao).emitir(usuario, FinalidadeToken.VERIFICACAO_EMAIL, destino)
    horas = int(VALIDADE[FinalidadeToken.VERIFICACAO_EMAIL].total_seconds() // 3600)
    link = f"{config.url_frontend}/verificar-email#token={token}"
    tarefas.add_task(email.enviar, email.verificacao(destino, usuario.nome, link, horas))


def avisar(
    usuario: Usuario,
    destino: str,
    titulo: str,
    config: Configuracoes,
    email: ServicoEmail,
    tarefas: BackgroundTasks,
) -> None:
    """Aviso de segurança ao dono da conta (troca de senha, pedido de troca de e-mail)."""
    mensagem = email.alerta(
        destino,
        usuario.nome,
        titulo,
        "Se não foi você, redefina sua senha agora e fale com o suporte.",
        f"{config.url_frontend}/esqueci-senha",
    )
    tarefas.add_task(email.enviar, mensagem)


@router.post(
    "/verificacao/solicitar",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reenvia o link de confirmação (do e-mail atual ou do pendente)",
    responses=RESPOSTAS,
)
def solicitar_verificacao(
    usuario: UsuarioDep,
    sessao: SessaoDep,
    config: ConfigDep,
    email: EmailDep,
    tarefas: BackgroundTasks,
) -> Response:
    destino = usuario.email_pendente or (None if usuario.email_verificado_em else usuario.email)
    if destino:
        LimitadorTentativas(sessao, config).reservar(
            "verificacao_email", email=chave_usuario(usuario)
        )
        enviar_verificacao(usuario, destino, sessao, config, email, tarefas)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post(
    "/verificacao/confirmar",
    response_model=UsuarioSaida,
    summary="Confirma o e-mail (atual ou o novo, numa troca) com o token do link",
    responses={
        409: {"description": "O novo e-mail passou a ser usado por outra conta"},
        422: {"description": "Link inválido ou expirado"},
    },
)
def confirmar_verificacao(dados: ConfirmacaoToken, sessao: SessaoDep) -> UsuarioSaida:
    usuario, registro = ServicoTokensConta(sessao).consumir(
        dados.token, FinalidadeToken.VERIFICACAO_EMAIL
    )
    if usuario.email_pendente and registro.email_alvo == usuario.email_pendente:
        try:
            ServicoUsuarios(sessao).aplicar_email_pendente(usuario)
        except Conflito:
            raise Conflito("Este e-mail passou a ser usado por outra conta.") from None
    elif registro.email_alvo == usuario.email:
        ServicoUsuarios(sessao).marcar_email_verificado(usuario)
    else:
        # O link foi enviado para um endereço que a conta não usa mais.
        sessao.rollback()
        raise TokenContaInvalido(MENSAGEM_INVALIDO)
    return UsuarioSaida.model_validate(usuario)


def processar_recuperacao(
    email_informado: str, fabrica: FabricaSessao, config: Configuracoes, email: ServicoEmail
) -> None:
    """Roda em segundo plano: a resposta HTTP sai antes, no mesmo tempo para qualquer e-mail."""
    with fabrica() as sessao:
        usuario = sessao.scalars(
            select(Usuario).where(Usuario.email == email_informado)
        ).one_or_none()
        if usuario is None or not usuario.ativo:
            return
        token = ServicoTokensConta(sessao).emitir(
            usuario, FinalidadeToken.RECUPERACAO_SENHA, usuario.email
        )
        minutos = int(VALIDADE[FinalidadeToken.RECUPERACAO_SENHA].total_seconds() // 60)
        link = f"{config.url_frontend}/redefinir-senha#token={token}"
        email.enviar(email.recuperacao_senha(usuario.email, usuario.nome, link, minutos))


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
    fabrica: FabricaDep,
    tarefas: BackgroundTasks,
) -> Response:
    """Sempre 202 e sem consultar a conta aqui: nem a resposta nem o tempo revelam se existe."""
    LimitadorTentativas(sessao, config).reservar(
        "recuperacao_senha", email=dados.email, ip=_ip(request)
    )
    tarefas.add_task(processar_recuperacao, dados.email, fabrica, config, email)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post(
    "/senha/redefinir",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Define uma nova senha com o token do link (derruba as sessões abertas)",
    responses={422: {"description": "Link inválido ou expirado, ou senha fraca"}},
)
def redefinir_senha(
    dados: RedefinicaoSenha,
    sessao: SessaoDep,
    config: ConfigDep,
    email: EmailDep,
    tarefas: BackgroundTasks,
) -> Response:
    servico_tokens = ServicoTokensConta(sessao)
    # A senha é validada antes de consumir o link: senha fraca não gasta o link.
    validar_senha(
        dados.nova_senha, servico_tokens.dono(dados.token, FinalidadeToken.RECUPERACAO_SENHA).email
    )
    usuario, registro = servico_tokens.consumir(dados.token, FinalidadeToken.RECUPERACAO_SENHA)
    if registro.email_alvo != usuario.email:  # o e-mail mudou depois do pedido
        sessao.rollback()
        raise TokenContaInvalido(MENSAGEM_INVALIDO)
    servico = ServicoUsuarios(sessao)
    # Quem recebeu o link no e-mail atual provou que controla esse endereço.
    servico.marcar_email_verificado(usuario, confirmar=False)
    servico.definir_senha(usuario, dados.nova_senha)
    avisar(usuario, usuario.email, "Sua senha foi alterada", config, email, tarefas)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
