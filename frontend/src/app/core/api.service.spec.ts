import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';

import { ApiService, ErroApi } from './api.service';

describe('ApiService', () => {
  let api: ApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(ApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('monta a URL a partir da base da API e envia parâmetros', async () => {
    const resposta = firstValueFrom(api.get<{ ok: boolean }>('/residencias', { pagina: 2 }));

    const req = http.expectOne('/api/v1/residencias?pagina=2');
    expect(req.request.method).toBe('GET');
    req.flush({ ok: true });

    expect(await resposta).toEqual({ ok: true });
  });

  it('converte o erro RFC 7807 em ErroApi com mensagem e campos', async () => {
    const resposta = firstValueFrom(api.post('residencias', { nome: '' }));

    http.expectOne('/api/v1/residencias').flush(
      {
        status: 422,
        title: 'Unprocessable Entity',
        detail: 'Dados inválidos.',
        erros: [{ campo: 'nome', mensagem: 'obrigatório' }],
      },
      { status: 422, statusText: 'Unprocessable Entity' },
    );

    const erro = await resposta.catch((e: unknown) => e);
    expect(erro).toBeInstanceOf(ErroApi);
    expect((erro as ErroApi).message).toBe('Dados inválidos.');
    expect((erro as ErroApi).erros).toEqual([{ campo: 'nome', mensagem: 'obrigatório' }]);
  });

  it('explica a falha de conexão em português', async () => {
    const resposta = firstValueFrom(api.delete('residencias/1'));

    http.expectOne('/api/v1/residencias/1').error(new ProgressEvent('error'), { status: 0 });

    const erro = (await resposta.catch((e: unknown) => e)) as ErroApi;
    expect(erro.status).toBe(0);
    expect(erro.message).toContain('Não foi possível conectar');
  });

  it('usa mensagem genérica quando a resposta não segue o RFC 7807', async () => {
    const resposta = firstValueFrom(api.put('x', {}));

    http.expectOne('/api/v1/x').flush('erro', { status: 500, statusText: 'Server Error' });

    const erro = (await resposta.catch((e: unknown) => e)) as ErroApi;
    expect(erro.message).toBe('Ocorreu um erro inesperado. Tente novamente.');
  });
});
