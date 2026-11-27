import { Component, OnInit, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';

import { ErroApi } from '../../core/api.service';
import { ContaService } from '../../core/conta.service';
import { lerTokenDaUrl } from './token-da-url';

type Estado = 'confirmando' | 'confirmado' | 'link-invalido' | 'em-uso' | 'falha-temporaria';

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
        @case ('link-invalido') {
          <p class="linha erro">
            <mat-icon aria-hidden="true">error</mat-icon>
            {{ mensagem() }}
          </p>
          <!-- O reenvio exige login; o link direto para ele chega com a tela de login (#36). -->
          <p>Entre na sua conta e peça um novo link de confirmação no seu perfil.</p>
          <a mat-stroked-button routerLink="/inicio">Voltar para o início</a>
        }
        @case ('em-uso') {
          <p class="linha erro">
            <mat-icon aria-hidden="true">error</mat-icon>
            {{ mensagem() }}
          </p>
          <p>Entre na sua conta e escolha outro e-mail no seu perfil.</p>
          <a mat-stroked-button routerLink="/inicio">Voltar para o início</a>
        }
        @case ('falha-temporaria') {
          <p class="linha erro">
            <mat-icon aria-hidden="true">wifi_off</mat-icon>
            {{ mensagem() }}
          </p>
          <!-- O token já saiu da URL; ele fica guardado aqui para tentar de novo. -->
          <button mat-flat-button type="button" (click)="confirmar()">Tentar de novo</button>
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
    this.confirmar();
  }

  confirmar(): void {
    if (!this.token) {
      this.falhar(
        'link-invalido',
        'O link está incompleto. Abra o endereço exatamente como veio no e-mail.',
      );
      return;
    }
    this.estado.set('confirmando');
    this.conta.confirmarEmail(this.token).subscribe({
      next: () => this.estado.set('confirmado'),
      error: (erro: ErroApi) => {
        if (erro.status === 0 || erro.status >= 500) {
          this.falhar('falha-temporaria', erro.message);
        } else if (erro.status === 409) {
          this.falhar('em-uso', erro.message);
        } else {
          this.falhar('link-invalido', erro.message);
        }
      },
    });
  }

  private falhar(estado: Estado, mensagem: string): void {
    this.mensagem.set(mensagem);
    this.estado.set(estado);
  }
}
