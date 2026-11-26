import { Routes } from '@angular/router';

import { Shell } from './layout/shell';

export const routes: Routes = [
  {
    path: '',
    component: Shell,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'inicio' },
      {
        path: 'inicio',
        title: 'Início · Agente de Economia',
        loadComponent: () => import('./paginas/inicio').then((m) => m.Inicio),
      },
      // Seções do menu ainda não construídas: página provisória em vez de 404.
      // As rotas de admin ganham guard na #36.
      ...[
        ['residencias', 'Minhas residências'],
        ['recomendacoes', 'Recomendações'],
        ['admin/usuarios', 'Usuários'],
        ['admin/categorias', 'Categorias'],
      ].map(([path, secao]) => ({
        path,
        title: `${secao} · Agente de Economia`,
        data: { secao },
        loadComponent: () => import('./paginas/em-breve').then((m) => m.EmBreve),
      })),
      {
        path: '**',
        title: 'Página não encontrada · Agente de Economia',
        loadComponent: () => import('./paginas/nao-encontrada').then((m) => m.NaoEncontrada),
      },
    ],
  },
];
