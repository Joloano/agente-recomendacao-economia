import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { SessaoService, UsuarioSessao } from '../core/sessao.service';
import { Shell } from './shell';

const cliente: UsuarioSessao = { id: '1', nome: 'Ana', email: 'ana@exemplo.com', papel: 'cliente' };

function renderizar(usuario: UsuarioSessao | null): HTMLElement {
  TestBed.configureTestingModule({
    imports: [Shell],
    providers: [provideRouter([])],
  });
  if (usuario) {
    TestBed.inject(SessaoService).iniciar(usuario);
  }
  const fixture = TestBed.createComponent(Shell);
  fixture.detectChanges();
  return fixture.nativeElement as HTMLElement;
}

function rotulosDoMenu(elemento: HTMLElement): string[] {
  return Array.from(elemento.querySelectorAll('[matlistitemtitle]')).map(
    (e) => e.textContent?.trim() ?? '',
  );
}

describe('Shell', () => {
  it('cliente não vê os itens de administração', () => {
    const elemento = renderizar(cliente);

    expect(rotulosDoMenu(elemento)).toEqual(['Início', 'Minhas residências', 'Recomendações']);
    expect(elemento.querySelector('[data-testid="usuario"]')?.textContent).toContain('Ana');
  });

  it('admin vê também os itens de administração', () => {
    const elemento = renderizar({ ...cliente, papel: 'admin' });

    expect(rotulosDoMenu(elemento)).toContain('Usuários');
    expect(rotulosDoMenu(elemento)).toContain('Categorias');
  });

  it('oferece atalho para pular direto ao conteúdo', () => {
    const elemento = renderizar(null);

    expect(elemento.querySelector('a.pular-para-conteudo')?.getAttribute('href')).toBe('#conteudo');
  });
});
