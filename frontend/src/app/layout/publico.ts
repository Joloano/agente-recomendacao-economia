import { Component } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink, RouterOutlet } from '@angular/router';

/** Layout das páginas abertas (sem login): um cartão centralizado com a marca. */
@Component({
  selector: 'app-publico',
  imports: [RouterOutlet, RouterLink, MatCardModule, MatIconModule],
  template: `
    <main class="fundo" id="conteudo">
      <mat-card appearance="outlined" class="cartao">
        <a class="marca" routerLink="/inicio" aria-label="Agente de Economia: página inicial">
          <mat-icon class="energia" aria-hidden="true">bolt</mat-icon>
          <mat-icon class="agua" aria-hidden="true">water_drop</mat-icon>
          <span>Agente de Economia</span>
        </a>
        <router-outlet />
      </mat-card>
    </main>
  `,
  styles: `
    .fundo {
      min-height: 100%;
      display: grid;
      place-items: center;
      padding: 1.5rem;
      box-sizing: border-box;
    }
    .cartao {
      width: min(100%, 28rem);
      padding: 2rem;
    }
    .marca {
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      margin-bottom: 1.5rem;
      color: inherit;
      text-decoration: none;
      font: var(--mat-sys-title-large);
    }
    .energia {
      color: var(--cor-energia);
    }
    .agua {
      color: var(--cor-agua);
    }
  `,
})
export class Publico {}
