# Frontend

Interface em Angular 22 com Angular Material 3. Visão geral e convenções no [AGENTS.md](../AGENTS.md).

## Desenvolvimento

```bash
cd frontend
npm ci
npm start          # http://localhost:4200 — /api é encaminhado para http://localhost:8000
```

## Qualidade

```bash
npm test -- --watch=false   # Vitest
npm run lint                # ESLint (angular-eslint)
npx prettier --check src    # formatação
npx ng build                # build de produção
```

## Estrutura

| Pasta | Responsabilidade |
|---|---|
| `src/app/core/` | Serviços transversais: `ApiService` (HTTP + erros RFC 7807) e `SessaoService` |
| `src/app/layout/` | `Shell` (barra, menu lateral responsivo) e itens de navegação |
| `src/app/paginas/` | Páginas carregadas sob demanda (lazy) |
| `src/environments/` | URL da API por ambiente |

## Regras

- Nenhuma regra de negócio no frontend: ela vive na API.
- Todo acesso HTTP passa pelo `ApiService`; erros chegam como `ErroApi` com mensagem em português.
- Cores de recurso: `--cor-energia` e `--cor-agua`, sempre acompanhadas de ícone e texto.
- Componentes standalone, `inject()`, sinais e o novo controle de fluxo (`@if`, `@for`).

## Orçamento do bundle

O aviso do bundle inicial é de 550 kB (cerca de 120 kB comprimidos). O `@angular/forms` entra no
bundle inicial porque o `MatListModule` do menu o importa; antes de haver formulários ele era
descartado pelo tree-shaking. Se o bundle crescer, revise o que está no `Shell` (que é carregado
logo de início) antes de aumentar o limite.
