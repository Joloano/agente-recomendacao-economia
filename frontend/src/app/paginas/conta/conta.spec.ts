import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Type } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { routes } from '../../app.routes';

import { EsqueciSenha } from './esqueci-senha';
import { RedefinirSenha } from './redefinir-senha';
import { VerificarEmail } from './verificar-email';

const TOKEN = 'a'.repeat(43);

function montar<T>(
  componente: Type<T>,
  token: string | null,
): {
  fixture: ComponentFixture<T>;
  http: HttpTestingController;
  navegar: ReturnType<typeof vi.spyOn>;
} {
  TestBed.configureTestingModule({
    imports: [componente],
    providers: [
      provideRouter([]),
      provideHttpClient(),
      provideHttpClientTesting(),
      {
        provide: ActivatedRoute,
        useValue: { snapshot: { fragment: token ? `token=${token}` : null } },
      },
    ],
  });
  const navegar = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
  const fixture = TestBed.createComponent(componente);
  fixture.detectChanges();
  return { fixture, http: TestBed.inject(HttpTestingController), navegar };
}

function texto(fixture: ComponentFixture<unknown>): string {
  fixture.detectChanges();
  return (fixture.nativeElement as HTMLElement).textContent ?? '';
}

describe('VerificarEmail', () => {
  it('confirma o e-mail e tira o token da URL', () => {
    const { fixture, http, navegar } = montar(VerificarEmail, TOKEN);

    const req = http.expectOne('/api/v1/auth/verificacao/confirmar');
    expect(req.request.body).toEqual({ token: TOKEN });
    req.flush({});

    expect(texto(fixture)).toContain('Seu e-mail foi confirmado');
    expect(navegar).toHaveBeenCalledWith([], expect.objectContaining({ replaceUrl: true }));
  });

  it('mostra a mensagem da API quando o link expirou', () => {
    const { fixture, http } = montar(VerificarEmail, TOKEN);

    http
      .expectOne('/api/v1/auth/verificacao/confirmar')
      .flush(
        { status: 422, title: 'Unprocessable Entity', detail: 'Este link é inválido ou expirou.' },
        { status: 422, statusText: 'Unprocessable Entity' },
      );

    expect(texto(fixture)).toContain('Este link é inválido ou expirou.');
  });

  it('sem token não chama a API', () => {
    const { fixture, http } = montar(VerificarEmail, null);

    http.expectNone('/api/v1/auth/verificacao/confirmar');
    expect(texto(fixture)).toContain('O link está incompleto');
  });
});

describe('EsqueciSenha', () => {
  it('valida o e-mail antes de enviar', () => {
    const { fixture, http } = montar(EsqueciSenha, null);
    fixture.componentInstance.email.setValue('sem-arroba');

    fixture.componentInstance.enviar();

    http.expectNone('/api/v1/auth/senha/esqueci');
    expect(texto(fixture)).toContain('Digite um e-mail válido');
  });

  it('depois de enviar mostra a mesma mensagem, exista a conta ou não', () => {
    const { fixture, http } = montar(EsqueciSenha, null);
    fixture.componentInstance.email.setValue(' ana@exemplo.com ');

    fixture.componentInstance.enviar();
    const req = http.expectOne('/api/v1/auth/senha/esqueci');
    expect(req.request.body).toEqual({ email: 'ana@exemplo.com' });
    req.flush(null, { status: 202, statusText: 'Accepted' });

    expect(texto(fixture)).toContain('Se houver uma conta com este e-mail');
  });
});

describe('RedefinirSenha', () => {
  it('recusa senhas diferentes sem chamar a API', () => {
    const { fixture, http } = montar(RedefinirSenha, TOKEN);
    fixture.componentInstance.formulario.setValue({
      senha: 'uma senha bem longa',
      confirmacao: 'outra senha bem longa',
    });

    fixture.componentInstance.salvar();

    http.expectNone('/api/v1/auth/senha/redefinir');
    expect(texto(fixture)).toContain('As senhas não são iguais');
  });

  it('envia a nova senha com o token e confirma', () => {
    const { fixture, http, navegar } = montar(RedefinirSenha, TOKEN);
    fixture.componentInstance.formulario.setValue({
      senha: 'uma senha bem longa',
      confirmacao: 'uma senha bem longa',
    });

    fixture.componentInstance.salvar();
    const req = http.expectOne('/api/v1/auth/senha/redefinir');
    expect(req.request.body).toEqual({ token: TOKEN, nova_senha: 'uma senha bem longa' });
    req.flush(null, { status: 204, statusText: 'No Content' });

    expect(texto(fixture)).toContain('Senha alterada');
    expect(navegar).toHaveBeenCalledWith([], expect.objectContaining({ replaceUrl: true }));
  });

  it('mostra o erro da API (ex.: senha comum)', () => {
    const { fixture, http } = montar(RedefinirSenha, TOKEN);
    fixture.componentInstance.formulario.setValue({
      senha: 'password123',
      confirmacao: 'password123',
    });

    fixture.componentInstance.salvar();
    http
      .expectOne('/api/v1/auth/senha/redefinir')
      .flush(
        { status: 422, title: 'Unprocessable Entity', detail: 'Esta senha é muito comum.' },
        { status: 422, statusText: 'Unprocessable Entity' },
      );

    expect(texto(fixture)).toContain('Esta senha é muito comum.');
  });
});

describe('Fluxos de conta: casos de borda', () => {
  it('confirmação: falha de conexão permite tentar de novo com o mesmo token', () => {
    const { fixture, http } = montar(VerificarEmail, TOKEN);

    http.expectOne('/api/v1/auth/verificacao/confirmar').error(new ProgressEvent('error'), {
      status: 0,
    });
    expect(texto(fixture)).toContain('Não foi possível conectar');

    (fixture.nativeElement as HTMLElement).querySelector('button')?.click();
    const nova = http.expectOne('/api/v1/auth/verificacao/confirmar');
    expect(nova.request.body).toEqual({ token: TOKEN });
    nova.flush({});

    expect(texto(fixture)).toContain('Seu e-mail foi confirmado');
  });

  it('confirmação: e-mail tomado por outra conta tem orientação própria', () => {
    const { fixture, http } = montar(VerificarEmail, TOKEN);

    http.expectOne('/api/v1/auth/verificacao/confirmar').flush(
      {
        status: 409,
        title: 'Conflict',
        detail: 'Este e-mail passou a ser usado por outra conta.',
      },
      { status: 409, statusText: 'Conflict' },
    );

    expect(texto(fixture)).toContain('escolha outro e-mail');
  });

  it('esqueci a senha: limite atingido mostra a mensagem e permite tentar depois', () => {
    const { fixture, http } = montar(EsqueciSenha, null);
    fixture.componentInstance.email.setValue('ana@exemplo.com');

    fixture.componentInstance.enviar();
    http
      .expectOne('/api/v1/auth/senha/esqueci')
      .flush(
        { status: 429, title: 'Too Many Requests', detail: 'Muitas tentativas seguidas.' },
        { status: 429, statusText: 'Too Many Requests' },
      );

    expect(texto(fixture)).toContain('Muitas tentativas seguidas.');
    expect(fixture.componentInstance.enviando()).toBe(false);
  });

  it('esqueci a senha: segundo clique durante o envio não repete a requisição', () => {
    const { fixture, http } = montar(EsqueciSenha, null);
    fixture.componentInstance.email.setValue('ana@exemplo.com');

    fixture.componentInstance.enviar();
    fixture.componentInstance.enviar();

    expect(http.match('/api/v1/auth/senha/esqueci')).toHaveLength(1);
  });

  it('nova senha: sem token mostra o caminho para pedir outro link', () => {
    const { fixture, http } = montar(RedefinirSenha, null);

    http.expectNone('/api/v1/auth/senha/redefinir');
    expect(texto(fixture)).toContain('O link está incompleto');
  });
});

describe('Rotas reais', () => {
  it('abre /verificar-email#token=..., tira o token da URL e confirma uma vez só', async () => {
    TestBed.configureTestingModule({
      providers: [provideRouter(routes), provideHttpClient(), provideHttpClientTesting()],
    });
    const harness = await RouterTestingHarness.create();
    const http = TestBed.inject(HttpTestingController);

    await harness.navigateByUrl(`/verificar-email#token=${TOKEN}`);
    await harness.fixture.whenStable();

    expect(TestBed.inject(Router).url).toBe('/verificar-email');
    const req = http.expectOne('/api/v1/auth/verificacao/confirmar');
    expect(req.request.body).toEqual({ token: TOKEN });
  });

  it('a raiz continua levando ao início', async () => {
    TestBed.configureTestingModule({
      providers: [provideRouter(routes), provideHttpClient(), provideHttpClientTesting()],
    });
    const harness = await RouterTestingHarness.create();

    await harness.navigateByUrl('/');

    expect(TestBed.inject(Router).url).toBe('/inicio');
  });
});
