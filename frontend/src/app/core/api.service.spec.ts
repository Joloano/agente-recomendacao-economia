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

  it.each([
    [
      'texto HTML de um proxy',
      '<html>502</html>',
      502,
      'Ocorreu um erro inesperado. Tente novamente.',
    ],
    ['corpo vazio', null, 404, 'Não encontramos o que você procurou.'],
    [
      'detail que repete o título em inglês',
      { status: 404, title: 'Not Found', detail: 'Not Found' },
      404,
      'Não encontramos o que você procurou.',
    ],
    [
      'detail vazio',
      { status: 409, title: 'Conflict', detail: ' ' },
      409,
      'Esta ação conflita com o estado atual. Atualize a página e tente de novo.',
    ],
    [
      '401 sem detalhe próprio',
      { status: 401, title: 'Unauthorized', detail: 'Unauthorized' },
      401,
      'Sua sessão expirou. Entre novamente.',
    ],
    [
      '401 com detalhe da API (login)',
      { status: 401, title: 'Unauthorized', detail: 'E-mail ou senha incorretos.' },
      401,
      'E-mail ou senha incorretos.',
    ],
  ])('traduz erro com %s', async (_caso, corpo, status, mensagem) => {
    const resposta = firstValueFrom(api.put('x', {}));

    http.expectOne('/api/v1/x').flush(corpo, { status, statusText: 'Erro' });

    const erro = (await resposta.catch((e: unknown) => e)) as ErroApi;
    expect(erro.status).toBe(status);
    expect(erro.message).toBe(mensagem);
  });
});
