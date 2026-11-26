import { BreakpointObserver, BreakpointState } from '@angular/cdk/layout';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { SessaoService, UsuarioSessao } from '../core/sessao.service';
import { Shell } from './shell';

const cliente: UsuarioSessao = { id: '1', nome: 'Ana', email: 'ana@exemplo.com', papel: 'cliente' };

function renderizar(usuario: UsuarioSessao | null, celular = false) {
  const tela = new BehaviorSubject<BreakpointState>({ matches: celular, breakpoints: {} });
  TestBed.configureTestingModule({
    imports: [Shell],
    providers: [
      provideRouter([]),
      { provide: BreakpointObserver, useValue: { observe: () => tela } },
    ],
  });
  if (usuario) {
    TestBed.inject(SessaoService).iniciar(usuario);
  }
  const fixture = TestBed.createComponent(Shell);
  fixture.detectChanges();
  return { fixture, elemento: fixture.nativeElement as HTMLElement };
}

function rotulosDoMenu(elemento: HTMLElement): string[] {
  return Array.from(elemento.querySelectorAll('[matlistitemtitle]')).map(
    (e) => e.textContent?.trim() ?? '',
  );
}

describe('Shell', () => {
  it('cliente não vê os itens de administração', () => {
    const { elemento } = renderizar(cliente);

    expect(rotulosDoMenu(elemento)).toEqual(['Início', 'Minhas residências', 'Recomendações']);
    expect(elemento.querySelector('[data-testid="usuario"]')?.textContent).toContain('Ana');
  });

  it('admin vê também os itens de administração', () => {
    const { elemento } = renderizar({ ...cliente, papel: 'admin' });

    expect(rotulosDoMenu(elemento)).toContain('Usuários');
    expect(rotulosDoMenu(elemento)).toContain('Categorias');
  });

  it('o atalho leva o foco ao conteúdo sem mudar de página', () => {
    const { elemento } = renderizar(null);
    document.body.appendChild(elemento);

    (elemento.querySelector('button.pular-para-conteudo') as HTMLButtonElement).click();

    expect(document.activeElement?.id).toBe('conteudo');
    elemento.remove();
  });

  it('no desktop o menu fica fixo e não há botão de menu', () => {
    const { elemento } = renderizar(cliente, false);

    expect(elemento.querySelector('mat-sidenav')?.classList).toContain('mat-drawer-side');
    expect(elemento.querySelector('[aria-controls="menu-principal"]')).toBeNull();
  });

  it('no celular o menu é uma gaveta com estado anunciado', async () => {
    const { fixture, elemento } = renderizar(cliente, true);
    const botao = elemento.querySelector('[aria-controls="menu-principal"]') as HTMLButtonElement;

    expect(elemento.querySelector('mat-sidenav')?.classList).toContain('mat-drawer-over');
    expect(botao.getAttribute('aria-expanded')).toBe('false');

    botao.click();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(botao.getAttribute('aria-expanded')).toBe('true');
  });
});
