import { TestBed } from '@angular/core/testing';

import { SessaoService } from './sessao.service';

describe('SessaoService', () => {
  it('começa sem usuário e reage ao papel de quem entra', () => {
    const sessao = TestBed.inject(SessaoService);
    expect(sessao.autenticado()).toBe(false);

    sessao.iniciar({ id: '1', nome: 'Ana', email: 'ana@exemplo.com', papel: 'admin' });
    expect(sessao.autenticado()).toBe(true);
    expect(sessao.ehAdmin()).toBe(true);

    sessao.encerrar();
    expect(sessao.usuario()).toBeNull();
    expect(sessao.ehAdmin()).toBe(false);
  });
});
