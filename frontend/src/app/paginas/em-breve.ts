import { Component, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

/** Página provisória das seções que ainda serão construídas (evita levar o usuário a um 404). */
@Component({
  selector: 'app-em-breve',
  imports: [MatButtonModule, MatIconModule, RouterLink],
  template: `
    <h1>{{ secao() }}</h1>
    <p>
      <mat-icon aria-hidden="true">construction</mat-icon>
      Esta seção está em construção e chega em breve.
    </p>
    <a mat-flat-button routerLink="/inicio">Voltar para o início</a>
  `,
})
export class EmBreve {
  /** Vem do `data` da rota (withComponentInputBinding). */
  readonly secao = input('Em breve');
}
