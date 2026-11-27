import { ElementRef, Injector, afterNextRender, inject } from '@angular/core';

/**
 * Leva o foco a um elemento depois da próxima renderização (ex.: o título de uma mensagem de
 * sucesso que acabou de aparecer). Sem isso, o botão que tinha o foco some e ele cai no <body>.
 */
export function criarFocoAposRender(): (alvo: () => ElementRef<HTMLElement> | undefined) => void {
  const injector = inject(Injector);
  return (alvo) => afterNextRender(() => alvo()?.nativeElement.focus(), { injector });
}
