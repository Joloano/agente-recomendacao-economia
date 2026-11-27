import { Component, inject, signal } from '@angular/core';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { RouterLink } from '@angular/router';

import { ErroApi } from '../../core/api.service';
import { ContaService } from '../../core/conta.service';
import { lerTokenDaUrl } from './token-da-url';

const TAMANHO_MINIMO = 10;

function senhasIguais(grupo: AbstractControl): ValidationErrors | null {
  const { senha, confirmacao } = grupo.value as { senha: string; confirmacao: string };
  return senha && confirmacao && senha !== confirmacao ? { diferentes: true } : null;
}

@Component({
  selector: 'app-redefinir-senha',
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    RouterLink,
  ],
  template: `
    <h1>Criar nova senha</h1>
    @if (concluido()) {
      <p class="linha sucesso" role="status">
        <mat-icon aria-hidden="true">check_circle</mat-icon>
        Senha alterada! Por segurança, você saiu de todos os aparelhos.
      </p>
      <a mat-flat-button routerLink="/inicio">Entrar com a nova senha</a>
    } @else if (!token) {
      <p class="linha erro" role="alert">
        <mat-icon aria-hidden="true">error</mat-icon>
        O link está incompleto. Peça um novo.
      </p>
      <a mat-stroked-button routerLink="/esqueci-senha">Pedir novo link</a>
    } @else {
      <form [formGroup]="formulario" (ngSubmit)="salvar()" novalidate>
        <mat-form-field appearance="outline" class="campo">
          <mat-label>Nova senha</mat-label>
          <input
            matInput
            [type]="visivel() ? 'text' : 'password'"
            autocomplete="new-password"
            formControlName="senha"
            required
          />
          <button
            mat-icon-button
            matSuffix
            type="button"
            (click)="visivel.set(!visivel())"
            [attr.aria-label]="visivel() ? 'Esconder senha' : 'Mostrar senha'"
            [attr.aria-pressed]="visivel()"
          >
            <mat-icon>{{ visivel() ? 'visibility_off' : 'visibility' }}</mat-icon>
          </button>
          <mat-hint>Use pelo menos {{ tamanhoMinimo }} caracteres; uma frase é ótima.</mat-hint>
          @if (formulario.controls.senha.hasError('minlength')) {
            <mat-error>A senha precisa ter pelo menos {{ tamanhoMinimo }} caracteres.</mat-error>
          }
        </mat-form-field>
        <mat-form-field appearance="outline" class="campo">
          <mat-label>Repita a nova senha</mat-label>
          <input
            matInput
            [type]="visivel() ? 'text' : 'password'"
            autocomplete="new-password"
            formControlName="confirmacao"
            required
          />
        </mat-form-field>
        @if (formulario.hasError('diferentes') && formulario.controls.confirmacao.touched) {
          <p class="erro" role="alert">As senhas não são iguais.</p>
        }
        @if (erro()) {
          <p class="erro" role="alert">{{ erro() }}</p>
        }
        <button mat-flat-button type="submit" [disabled]="salvando()">
          {{ salvando() ? 'Salvando...' : 'Salvar nova senha' }}
        </button>
      </form>
    }
  `,
  styleUrl: './conta.scss',
})
export class RedefinirSenha {
  private readonly conta = inject(ContaService);

  readonly token = lerTokenDaUrl();
  readonly tamanhoMinimo = TAMANHO_MINIMO;
  readonly formulario = new FormGroup(
    {
      senha: new FormControl('', {
        nonNullable: true,
        validators: [Validators.required, Validators.minLength(TAMANHO_MINIMO)],
      }),
      confirmacao: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    },
    { validators: senhasIguais },
  );
  readonly visivel = signal(false);
  readonly salvando = signal(false);
  readonly concluido = signal(false);
  readonly erro = signal('');

  salvar(): void {
    this.formulario.markAllAsTouched();
    if (!this.token || this.formulario.invalid || this.salvando()) {
      return;
    }
    this.salvando.set(true);
    this.erro.set('');
    this.conta.redefinirSenha(this.token, this.formulario.controls.senha.value).subscribe({
      next: () => this.concluido.set(true),
      error: (erro: ErroApi) => {
        this.erro.set(erro.message);
        this.salvando.set(false);
      },
    });
  }
}
