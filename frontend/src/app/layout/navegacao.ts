export interface ItemNavegacao {
  rotulo: string;
  icone: string;
  rota: string;
  soAdmin?: boolean;
}

/** Itens do menu lateral, na ordem em que aparecem. Rótulos óbvios (Krug, #54). */
export const ITENS_NAVEGACAO: readonly ItemNavegacao[] = [
  { rotulo: 'Início', icone: 'home', rota: '/inicio' },
  { rotulo: 'Minhas residências', icone: 'house', rota: '/residencias' },
  { rotulo: 'Recomendações', icone: 'lightbulb', rota: '/recomendacoes' },
  { rotulo: 'Usuários', icone: 'group', rota: '/admin/usuarios', soAdmin: true },
  { rotulo: 'Categorias', icone: 'category', rota: '/admin/categorias', soAdmin: true },
];
