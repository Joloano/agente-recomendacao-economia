import { Component } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

/** Página inicial. O painel com economia e próxima recomendação chega com as telas (#38, #54). */
@Component({
  selector: 'app-inicio',
  imports: [MatCardModule, MatIconModule],
  template: `
    <h1>Quanto você pode economizar hoje?</h1>
    <div class="cartoes">
      <mat-card appearance="outlined">
        <mat-card-header>
          <mat-icon matCardAvatar class="energia" aria-hidden="true">bolt</mat-icon>
          <mat-card-title>Energia</mat-card-title>
        </mat-card-header>
        <mat-card-content>Cadastre seus equipamentos para ver recomendações.</mat-card-content>
      </mat-card>
      <mat-card appearance="outlined">
        <mat-card-header>
          <mat-icon matCardAvatar class="agua" aria-hidden="true">water_drop</mat-icon>
          <mat-card-title>Água</mat-card-title>
        </mat-card-header>
        <mat-card-content>Cadastre seus equipamentos para ver recomendações.</mat-card-content>
      </mat-card>
    </div>
  `,
  styles: `
    .cartoes {
      display: grid;
      gap: 1rem;
      grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
    }
    .energia {
      color: var(--cor-energia);
    }
    .agua {
      color: var(--cor-agua);
    }
  `,
})
export class Inicio {}
