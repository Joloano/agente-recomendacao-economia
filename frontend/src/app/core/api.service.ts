import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

import { environment } from '../../environments/environment';

/** Erro no formato RFC 7807 devolvido pela API. */
export interface Problema {
  status: number;
  title: string;
  detail: string;
  instance?: string;
  erros?: { campo: string; mensagem: string }[];
}

/** Erro já traduzido para a interface: sempre tem uma mensagem em português. */
export class ErroApi extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly erros: Problema['erros'] = [],
  ) {
    super(message);
    this.name = 'ErroApi';
  }

  static de(resposta: HttpErrorResponse): ErroApi {
    if (resposta.status === 0) {
      return new ErroApi(0, 'Não foi possível conectar ao servidor. Verifique sua conexão.');
    }
    const problema = resposta.error as Partial<Problema> | null;
    const mensagem = problema?.detail ?? 'Ocorreu um erro inesperado. Tente novamente.';
    return new ErroApi(resposta.status, mensagem, problema?.erros ?? []);
  }
}

type Parametros = Record<string, string | number | boolean>;

/**
 * Único ponto de acesso HTTP à API: monta a URL base e converte erros em `ErroApi`.
 * Os serviços de cada funcionalidade usam esta classe em vez do HttpClient direto.
 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.urlApi;

  get<T>(caminho: string, parametros?: Parametros): Observable<T> {
    const params = new HttpParams({ fromObject: parametros ?? {} });
    return this.tratar(this.http.get<T>(this.url(caminho), { params }));
  }

  post<T>(caminho: string, corpo: unknown): Observable<T> {
    return this.tratar(this.http.post<T>(this.url(caminho), corpo));
  }

  put<T>(caminho: string, corpo: unknown): Observable<T> {
    return this.tratar(this.http.put<T>(this.url(caminho), corpo));
  }

  delete<T>(caminho: string): Observable<T> {
    return this.tratar(this.http.delete<T>(this.url(caminho)));
  }

  private url(caminho: string): string {
    return `${this.base}/${caminho.replace(/^\//, '')}`;
  }

  private tratar<T>(requisicao: Observable<T>): Observable<T> {
    return requisicao.pipe(
      catchError((erro: HttpErrorResponse) => throwError(() => ErroApi.de(erro))),
    );
  }
}
