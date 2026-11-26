/** Configuração de produção: o nginx encaminha `/api` para o backend (mesma origem). */
export const environment = {
  producao: true,
  urlApi: '/api/v1',
};
