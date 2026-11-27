import { Routes } from '@angular/router';

import { Shell } from './layout/shell';

export const routes: Routes = [
  // Páginas abertas (sem login), abertas pelos links enviados por e-mail. Cada uma tem o
  // próprio caminho com o layout público; um grupo sem caminho capturaria também a raiz "/".
  ...(
    [
      [
        'verificar-email',
        'Confirmar e-mail',
        () => import('./paginas/conta/verificar-email').then((m) => m.VerificarEmail),
      ],
      [
        'esqueci-senha',
        'Esqueci a senha',
        () => import('./paginas/conta/esqueci-senha').then((m) => m.EsqueciSenha),
      ],
      [
        'redefinir-senha',
        'Nova senha',
        () => import('./paginas/conta/redefinir-senha').then((m) => m.RedefinirSenha),
      ],
    ] as const
  ).map(([path, titulo, loadComponent]) => ({
    path,
    // Sob demanda: o layout público (e o MatCard) fica fora do bundle inicial.
    loadComponent: () => import('./layout/publico').then((m) => m.Publico),
    children: [{ path: '', title: `${titulo} · Agente de Economia`, loadComponent }],
  })),
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
