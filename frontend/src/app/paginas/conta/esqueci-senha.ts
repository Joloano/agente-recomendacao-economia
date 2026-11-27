import { Component, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { RouterLink } from '@angular/router';

import { ErroApi } from '../../core/api.service';
import { ContaService } from '../../core/conta.service';

@Component({
  selector: 'app-esqueci-senha',
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    RouterLink,
  ],
  template: `
    <h1>Esqueceu a senha?</h1>
    @if (enviado()) {
      <p class="linha sucesso" role="status">
        <mat-icon aria-hidden="true">mark_email_read</mat-icon>
        Se houver uma conta com este e-mail, enviamos um link para criar uma nova senha.
      </p>
      <p>O link vale por 30 minutos. Confira também a caixa de spam.</p>
      <a mat-stroked-button routerLink="/inicio">Voltar para o início</a>
    } @else {
      <p>Informe o e-mail da sua conta e enviaremos um link para criar uma nova senha.</p>
      <form (ngSubmit)="enviar()" novalidate>
        <mat-form-field appearance="outline" class="campo">
          <mat-label>E-mail</mat-label>
          <input matInput type="email" autocomplete="email" [formControl]="email" required />
          @if (email.hasError('required')) {
            <mat-error>Informe o e-mail.</mat-error>
          } @else if (email.hasError('email')) {
            <mat-error>Digite um e-mail válido, como nome&#64;exemplo.com.</mat-error>
          }
        </mat-form-field>
        @if (erro()) {
          <p class="erro" role="alert">{{ erro() }}</p>
        }
        <button mat-flat-button type="submit" [disabled]="enviando()">
          {{ enviando() ? 'Enviando...' : 'Enviar link' }}
        </button>
      </form>
    }
  `,
  styleUrl: './conta.scss',
})
export class EsqueciSenha {
  private readonly conta = inject(ContaService);

  readonly email = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.email],
  });
  readonly enviando = signal(false);
  readonly enviado = signal(false);
  readonly erro = signal('');

  enviar(): void {
    // E-mail colado com espaços nas pontas não deve virar erro de validação.
    this.email.setValue(this.email.value.trim());
    this.email.markAsTouched();
    if (this.email.invalid || this.enviando()) {
      return;
    }
    this.enviando.set(true);
    this.erro.set('');
    this.conta.pedirRecuperacao(this.email.value).subscribe({
      next: () => this.enviado.set(true),
      error: (erro: ErroApi) => {
        this.erro.set(erro.message);
        this.enviando.set(false);
      },
    });
  }
}
