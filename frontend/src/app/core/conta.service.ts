import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';
import { UsuarioSessao } from './sessao.service';

/** Fluxos de conta que não exigem login: confirmar e-mail e recuperar a senha. */
@Injectable({ providedIn: 'root' })
export class ContaService {
  private readonly api = inject(ApiService);

  confirmarEmail(token: string): Observable<UsuarioSessao> {
    return this.api.post<UsuarioSessao>('auth/verificacao/confirmar', { token });
  }

  pedirRecuperacao(email: string): Observable<void> {
    return this.api.post<void>('auth/senha/esqueci', { email });
  }

  redefinirSenha(token: string, novaSenha: string): Observable<void> {
    return this.api.post<void>('auth/senha/redefinir', { token, nova_senha: novaSenha });
  }
}
