import { inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

/**
 * Lê o token do fragmento do link (`#token=...`) uma única vez e o remove da barra de endereço.
 *
 * O fragmento nunca é enviado ao servidor (não aparece em logs nem no Referer), e a remoção
 * com `replaceUrl` tira o token também do histórico do navegador.
 * Deve ser chamado num contexto de injeção (construtor ou inicializador de campo).
 */
export function lerTokenDaUrl(): string | null {
  const rota = inject(ActivatedRoute);
  const router = inject(Router);
  const token = new URLSearchParams(rota.snapshot.fragment ?? '').get('token');
  if (token) {
    void router.navigate([], { relativeTo: rota, fragment: undefined, replaceUrl: true });
  }
  return token;
}
