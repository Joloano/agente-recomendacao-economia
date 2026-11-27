"""Casos de uso de usuários: criação, gestão pelo admin e o próprio perfil."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.erros import Conflito, DadosRecusados, NaoAutenticado, NaoEncontrado
from app.core.seguranca import SenhaFraca, gerar_hash, validar_politica_senha, verificar_senha
from app.esquemas.paginacao import ParametrosPagina
from app.esquemas.usuarios import PerfilAtualizacao, TrocaSenha, UsuarioAtualizacaoAdmin
from app.modelos import Papel, Usuario
from app.servicos.tokens_conta import ServicoTokensConta

MENSAGEM_EMAIL_EM_USO = "Este e-mail já está cadastrado."
MENSAGEM_ULTIMO_ADMIN = "É preciso manter pelo menos um administrador ativo."


class SenhaRecusada(DadosRecusados):
    """Senha fora da política mínima."""


class SenhaAtualIncorreta(NaoAutenticado):
    """A senha atual informada na troca de senha não confere."""


def _constraint_violada(erro: IntegrityError) -> str | None:
    diagnostico = getattr(erro.orig, "diag", None)
    return getattr(diagnostico, "constraint_name", None)


def validar_senha(senha: str, email: str) -> None:
    try:
        validar_politica_senha(senha, email)
    except SenhaFraca as erro:
        raise SenhaRecusada(str(erro)) from erro


def _escapar_like(texto: str) -> str:
    """Busca literal: "%" e "_" digitados pelo admin não viram curingas."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ServicoUsuarios:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    # ---------- base ----------
    def criar(
        self,
        nome: str,
        email: str,
        senha: str,
        papel: Papel,
        mensagem_conflito: str = MENSAGEM_EMAIL_EM_USO,
    ) -> Usuario:
        validar_senha(senha, email)
        usuario = Usuario(nome=nome, email=email, senha_hash=gerar_hash(senha), papel=papel)
        self._sessao.add(usuario)
        self._confirmar(mensagem_conflito)
        self._sessao.refresh(usuario)
        return usuario

    def obter(self, usuario_id: uuid.UUID) -> Usuario:
        usuario = self._sessao.get(Usuario, usuario_id)
        if usuario is None:
            raise NaoEncontrado("Usuário não encontrado.")
        return usuario

    def _confirmar(self, mensagem_conflito: str = MENSAGEM_EMAIL_EM_USO) -> None:
        try:
            self._sessao.commit()
        except IntegrityError as erro:
            self._sessao.rollback()
            # Só a unicidade do e-mail vira 409; outra violação é bug e deve aparecer.
            if _constraint_violada(erro) != "uq_usuario_email":
                raise
            raise Conflito(mensagem_conflito) from erro

    # ---------- admin ----------
    def listar(
        self,
        pagina: ParametrosPagina,
        busca: str | None = None,
        papel: Papel | None = None,
        ativo: bool | None = None,
    ) -> tuple[Sequence[Usuario], int]:
        filtros = []
        if busca:
            termo = f"%{_escapar_like(busca.strip().lower())}%"
            filtros.append(
                or_(
                    func.lower(Usuario.nome).like(termo, escape="\\"),
                    Usuario.email.like(termo, escape="\\"),
                )
            )
        if papel is not None:
            filtros.append(Usuario.papel == papel)
        if ativo is not None:
            filtros.append(Usuario.ativo == ativo)
        total = self._sessao.scalar(select(func.count()).select_from(Usuario).where(*filtros)) or 0
        itens = self._sessao.scalars(
            select(Usuario)
            .where(*filtros)
            .order_by(Usuario.criado_em.desc(), Usuario.id)
            .offset(pagina.deslocamento)
            .limit(pagina.tamanho)
        ).all()
        return itens, total

    def atualizar(
        self, usuario_id: uuid.UUID, dados: UsuarioAtualizacaoAdmin, solicitante: Usuario
    ) -> Usuario:
        perde_admin = dados.papel is Papel.CLIENTE or dados.ativo is False
        if perde_admin and usuario_id == solicitante.id:
            raise Conflito("Você não pode rebaixar nem desativar a própria conta.")
        if perde_admin:
            self._travar_admins_e_garantir_outro(usuario_id)
        usuario = self.obter(usuario_id)
        if dados.email is not None and dados.email != usuario.email:
            # Troca feita pelo admin vale na hora, mas o endereço precisa ser confirmado,
            # os links antigos caem e as sessões do usuário são derrubadas.
            usuario.email_verificado_em = None
            usuario.email_pendente = None
            usuario.versao_credenciais += 1
            ServicoTokensConta(self._sessao).invalidar(usuario, confirmar=False)
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(usuario, campo, valor)
        self._confirmar()
        return usuario

    def excluir(self, usuario_id: uuid.UUID, solicitante: Usuario) -> None:
        if usuario_id == solicitante.id:
            raise Conflito("Você não pode excluir a própria conta por esta área.")
        self._travar_admins_e_garantir_outro(usuario_id)
        self._sessao.delete(self.obter(usuario_id))
        self._sessao.commit()

    def _travar_admins_e_garantir_outro(self, alvo_id: uuid.UUID) -> None:
        """Trava todos os admins ativos (inclusive o alvo), sempre na mesma ordem.

        A ordem fixa evita deadlock entre requisições simultâneas: a segunda espera a
        primeira terminar e então reavalia com os dados já atualizados. Se o alvo não é
        admin ativo, a regra não se aplica.
        """
        admins = self._sessao.scalars(
            select(Usuario.id)
            .where(Usuario.papel == Papel.ADMIN, Usuario.ativo)
            .order_by(Usuario.id)
            .with_for_update()
        ).all()
        if alvo_id in admins and len(admins) < 2:  # noqa: PLR2004
            raise Conflito(MENSAGEM_ULTIMO_ADMIN)
        # Recarrega o alvo: o que outra transação gravou antes do lock passa a valer aqui.
        if (alvo := self._sessao.get(Usuario, alvo_id)) is not None:
            self._sessao.refresh(alvo)

    # ---------- próprio perfil ----------
    def atualizar_perfil(self, usuario: Usuario, dados: PerfilAtualizacao) -> str | None:
        """Atualiza o perfil. Um e-mail novo fica **pendente** até ser confirmado.

        Devolve o e-mail pendente quando houve pedido de troca (para enviar a confirmação).
        """
        mudancas = dados.model_dump(exclude_unset=True, exclude={"senha_atual", "email"})
        novo_email = dados.email if dados.email not in (None, usuario.email) else None
        # Trocar o e-mail exige a senha: um token roubado não basta para tomar a conta.
        if novo_email and not (
            dados.senha_atual and verificar_senha(dados.senha_atual, usuario.senha_hash)
        ):
            raise SenhaAtualIncorreta("Confirme a senha atual para trocar o e-mail.")
        if novo_email and self._sessao.scalar(
            select(Usuario.id).where(Usuario.email == novo_email)
        ):
            raise Conflito(MENSAGEM_EMAIL_EM_USO)
        for campo, valor in mudancas.items():
            setattr(usuario, campo, valor)
        if novo_email:
            usuario.email_pendente = novo_email
        self._confirmar()
        return novo_email

    def aplicar_email_pendente(self, usuario: Usuario) -> None:
        """O novo endereço confirmou: passa a valer, derruba as sessões e os links antigos."""
        assert usuario.email_pendente  # noqa: S101 - garantido por quem chama
        usuario.email = usuario.email_pendente
        usuario.email_pendente = None
        usuario.email_verificado_em = datetime.now(UTC)
        usuario.versao_credenciais += 1
        ServicoTokensConta(self._sessao).invalidar(usuario, confirmar=False)
        self._confirmar()

    def marcar_email_verificado(self, usuario: Usuario, *, confirmar: bool = True) -> None:
        usuario.email_verificado_em = usuario.email_verificado_em or datetime.now(UTC)
        if confirmar:
            self._sessao.commit()

    def trocar_senha(self, usuario: Usuario, dados: TrocaSenha) -> None:
        if not verificar_senha(dados.senha_atual, usuario.senha_hash):
            raise SenhaAtualIncorreta("A senha atual não confere.")
        if verificar_senha(dados.nova_senha, usuario.senha_hash):
            raise SenhaRecusada("A nova senha precisa ser diferente da atual.")
        validar_senha(dados.nova_senha, usuario.email)
        self.definir_senha(usuario, dados.nova_senha)

    def definir_senha(self, usuario: Usuario, nova_senha: str) -> None:
        """Grava a senha, derruba as sessões abertas e invalida os links pendentes."""
        usuario.senha_hash = gerar_hash(nova_senha)
        usuario.versao_credenciais += 1
        ServicoTokensConta(self._sessao).invalidar(usuario, confirmar=False)
        self._sessao.commit()
