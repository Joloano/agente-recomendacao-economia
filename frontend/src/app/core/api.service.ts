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

/** Mensagens usadas quando a API não envia um `detail` próprio em português. */
const MENSAGENS_POR_STATUS: Record<number, string> = {
  0: 'Não foi possível conectar ao servidor. Verifique sua conexão.',
  400: 'Não foi possível concluir a ação. Revise os dados e tente de novo.',
  401: 'Sua sessão expirou. Entre novamente.',
  403: 'Você não tem permissão para fazer isso.',
  404: 'Não encontramos o que você procurou.',
  409: 'Esta ação conflita com o estado atual. Atualize a página e tente de novo.',
  422: 'Dados inválidos. Revise os campos destacados.',
  429: 'Muitas tentativas seguidas. Aguarde um pouco e tente de novo.',
};
const MENSAGEM_GENERICA = 'Ocorreu um erro inesperado. Tente novamente.';

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
    const problema = ehProblema(resposta.error) ? resposta.error : null;
    const padrao = MENSAGENS_POR_STATUS[resposta.status] ?? MENSAGEM_GENERICA;
    // O `detail` da nossa API vem em português. Quando ele só repete o título HTTP
    // (ex.: "Not Found" do Starlette), ou vem vazio, usamos a mensagem do status.
    const detalheProprio =
      problema && problema.detail.trim() !== '' && problema.detail !== problema.title;
    const mensagem = detalheProprio ? problema.detail : padrao;
    return new ErroApi(resposta.status, mensagem, problema?.erros ?? []);
  }
}

function ehProblema(corpo: unknown): corpo is Problema {
  return (
    typeof corpo === 'object' && corpo !== null && typeof (corpo as Problema).detail === 'string'
  );
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
