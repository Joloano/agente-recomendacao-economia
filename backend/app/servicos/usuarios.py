"""Casos de uso de usuários: criação, gestão pelo admin e o próprio perfil."""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.erros import Conflito, DadosRecusados, NaoAutenticado, NaoEncontrado
from app.core.seguranca import SenhaFraca, gerar_hash, validar_politica_senha, verificar_senha
from app.esquemas.paginacao import ParametrosPagina
from app.esquemas.usuarios import PerfilAtualizacao, TrocaSenha, UsuarioAtualizacaoAdmin
from app.modelos import Papel, Usuario

MENSAGEM_EMAIL_EM_USO = "Este e-mail já está cadastrado."
MENSAGEM_ULTIMO_ADMIN = "É preciso manter pelo menos um administrador ativo."


class SenhaRecusada(DadosRecusados):
    """Senha fora da política mínima."""


class SenhaAtualIncorreta(NaoAutenticado):
    """A senha atual informada na troca de senha não confere."""


def _constraint_violada(erro: IntegrityError) -> str | None:
    diagnostico = getattr(erro.orig, "diag", None)
    return getattr(diagnostico, "constraint_name", None)


def _validar_senha(senha: str, email: str) -> None:
    try:
        validar_politica_senha(senha, email)
    except SenhaFraca as erro:
        raise SenhaRecusada(str(erro)) from erro


class ServicoUsuarios:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    # ---------- base ----------
    def criar(self, nome: str, email: str, senha: str, papel: Papel) -> Usuario:
        _validar_senha(senha, email)
        usuario = Usuario(nome=nome, email=email, senha_hash=gerar_hash(senha), papel=papel)
        self._sessao.add(usuario)
        self._confirmar()
        self._sessao.refresh(usuario)
        return usuario

    def obter(self, usuario_id: uuid.UUID) -> Usuario:
        usuario = self._sessao.get(Usuario, usuario_id)
        if usuario is None:
            raise NaoEncontrado("Usuário não encontrado.")
        return usuario

    def _confirmar(self) -> None:
        try:
            self._sessao.commit()
        except IntegrityError as erro:
            self._sessao.rollback()
            # Só a unicidade do e-mail vira 409; outra violação é bug e deve aparecer.
            if _constraint_violada(erro) != "uq_usuario_email":
                raise
            raise Conflito(MENSAGEM_EMAIL_EM_USO) from erro

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
            termo = f"%{busca.strip().lower()}%"
            filtros.append(or_(func.lower(Usuario.nome).like(termo), Usuario.email.like(termo)))
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

    def atualizar(self, usuario_id: uuid.UUID, dados: UsuarioAtualizacaoAdmin) -> Usuario:
        usuario = self.obter(usuario_id)
        perde_admin = (
            usuario.papel is Papel.ADMIN
            and usuario.ativo
            and (dados.papel is Papel.CLIENTE or dados.ativo is False)
        )
        if perde_admin:
            self._garantir_outro_admin(usuario)
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            if valor is not None:
                setattr(usuario, campo, valor)
        self._confirmar()
        return usuario

    def excluir(self, usuario_id: uuid.UUID, solicitante: Usuario) -> None:
        usuario = self.obter(usuario_id)
        if usuario.id == solicitante.id:
            raise Conflito("Use a exclusão da própria conta para apagar a sua conta.")
        if usuario.papel is Papel.ADMIN and usuario.ativo:
            self._garantir_outro_admin(usuario)
        self._sessao.delete(usuario)
        self._sessao.commit()

    def _garantir_outro_admin(self, usuario: Usuario) -> None:
        """Trava as linhas dos admins ativos: requisições simultâneas não esvaziam o sistema."""
        outros = self._sessao.scalars(
            select(Usuario.id)
            .where(Usuario.papel == Papel.ADMIN, Usuario.ativo, Usuario.id != usuario.id)
            .with_for_update()
        ).all()
        if not outros:
            raise Conflito(MENSAGEM_ULTIMO_ADMIN)

    # ---------- próprio perfil ----------
    def atualizar_perfil(self, usuario: Usuario, dados: PerfilAtualizacao) -> Usuario:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            if valor is not None:
                setattr(usuario, campo, valor)
        self._confirmar()
        return usuario

    def trocar_senha(self, usuario: Usuario, dados: TrocaSenha) -> None:
        if not verificar_senha(dados.senha_atual, usuario.senha_hash):
            raise SenhaAtualIncorreta("A senha atual não confere.")
        if verificar_senha(dados.nova_senha, usuario.senha_hash):
            raise SenhaRecusada("A nova senha precisa ser diferente da atual.")
        _validar_senha(dados.nova_senha, usuario.email)
        usuario.senha_hash = gerar_hash(dados.nova_senha)
        self._sessao.commit()
