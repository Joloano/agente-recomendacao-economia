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
      {
        path: '**',
        title: 'Página não encontrada · Agente de Economia',
        loadComponent: () => import('./paginas/nao-encontrada').then((m) => m.NaoEncontrada),
      },
    ],
  },
];
