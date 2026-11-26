import { Injectable, computed, signal } from '@angular/core';

export type Papel = 'admin' | 'cliente';

export interface UsuarioSessao {
  id: string;
  nome: string;
  email: string;
  papel: Papel;
}

/**
 * Estado da sessão do usuário. O login real (JWT) chega na #36; por enquanto o serviço só
 * guarda o usuário em memória, e as telas já reagem ao papel por meio dos sinais.
 */
@Injectable({ providedIn: 'root' })
export class SessaoService {
  private readonly usuarioAtual = signal<UsuarioSessao | null>(null);

  readonly usuario = this.usuarioAtual.asReadonly();
  readonly autenticado = computed(() => this.usuarioAtual() !== null);
  readonly ehAdmin = computed(() => this.usuarioAtual()?.papel === 'admin');

  iniciar(usuario: UsuarioSessao): void {
    this.usuarioAtual.set(usuario);
  }

  encerrar(): void {
    this.usuarioAtual.set(null);
  }
}
