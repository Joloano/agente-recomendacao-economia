import { Component, OnInit, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { ErroApi } from '../../core/api.service';
import { ContaService } from '../../core/conta.service';
import { lerTokenDaUrl } from './token-da-url';

type Estado = 'confirmando' | 'confirmado' | 'erro';

@Component({
  selector: 'app-verificar-email',
  imports: [MatButtonModule, MatIconModule, MatProgressSpinnerModule, RouterLink],
  template: `
    <h1>Confirmação de e-mail</h1>
    <div role="status" aria-live="polite">
      @switch (estado()) {
        @case ('confirmando') {
          <p class="linha">
            <mat-progress-spinner mode="indeterminate" diameter="24" aria-hidden="true" />
            Confirmando seu e-mail...
          </p>
        }
        @case ('confirmado') {
          <p class="linha sucesso">
            <mat-icon aria-hidden="true">check_circle</mat-icon>
            Pronto! Seu e-mail foi confirmado.
          </p>
          <a mat-flat-button routerLink="/inicio">Ir para o início</a>
        }
        @case ('erro') {
          <p class="linha erro">
            <mat-icon aria-hidden="true">error</mat-icon>
            {{ mensagem() }}
          </p>
          <p>Entre na sua conta para pedir um novo link de confirmação.</p>
          <a mat-stroked-button routerLink="/inicio">Voltar para o início</a>
        }
      }
    </div>
  `,
  styleUrl: './conta.scss',
})
export class VerificarEmail implements OnInit {
  private readonly conta = inject(ContaService);
  private readonly token = lerTokenDaUrl();

  readonly estado = signal<Estado>('confirmando');
  readonly mensagem = signal('');

  ngOnInit(): void {
    if (!this.token) {
      this.falhar('O link está incompleto. Abra o endereço exatamente como veio no e-mail.');
      return;
    }
    this.conta.confirmarEmail(this.token).subscribe({
      next: () => this.estado.set('confirmado'),
      error: (erro: ErroApi) => this.falhar(erro.message),
    });
  }

  private falhar(mensagem: string): void {
    this.mensagem.set(mensagem);
    this.estado.set('erro');
  }
}
