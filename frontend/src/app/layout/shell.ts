import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { map } from 'rxjs';

import { SessaoService } from '../core/sessao.service';
import { ITENS_NAVEGACAO } from './navegacao';

/** Layout da aplicação: barra superior, menu lateral responsivo e área de conteúdo. */
@Component({
  selector: 'app-shell',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
  ],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  private readonly sessao = inject(SessaoService);

  readonly usuario = this.sessao.usuario;
  readonly celular = toSignal(
    inject(BreakpointObserver)
      .observe(Breakpoints.Handset)
      .pipe(map((resultado) => resultado.matches)),
    { initialValue: false },
  );
  readonly itens = computed(() =>
    ITENS_NAVEGACAO.filter((item) => !item.soAdmin || this.sessao.ehAdmin()),
  );
}
