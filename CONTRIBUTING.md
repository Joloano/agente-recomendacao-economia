# Como contribuir

Este é um software proprietário (veja [LICENSE](LICENSE)). Contribuições só com autorização do titular.
Antes de começar, leia o [AGENTS.md](AGENTS.md).

## Fluxo de trabalho

1. **Escolha uma issue** no [quadro do projeto](https://github.com/users/Joloano/projects/2), mova para *Em andamento* e atribua a você.
2. **Crie a branch** a partir da `main` atualizada:
   `<tipo>/<numero-da-issue>-<descricao-curta>` — ex.: `feat/32-nucleo-do-agente`.
3. **Desenvolva** em commits pequenos, seguindo [Conventional Commits](#commits).
4. **Rode as verificações locais** (`pre-commit run --all-files` e os testes).
5. **Abra o PR** usando o template, com `Closes #<n>` e o checklist da Definição de Pronto marcado.
6. **Code review**: pelo menos uma revisão; comentários resolvidos antes do merge.
7. **Merge** só com CI verde, sempre por *squash* (o título do PR vira o commit na `main`). A branch é apagada após o merge.

## Commits

Formato: `<tipo>(<escopo opcional>): <descrição no imperativo, em português>`

| Tipo | Uso |
|---|---|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `docs` | Somente documentação |
| `refactor` | Mudança de código sem alterar comportamento |
| `test` | Testes |
| `build` / `ci` | Docker, dependências, pipelines |
| `chore` | Tarefas de manutenção |
| `perf` | Desempenho |

Exemplos: `feat(agente): adiciona estratégia de água`, `fix(api): impede feedback duplicado`.
Mudança incompatível: `feat!: ...` e um rodapé `BREAKING CHANGE: ...`.

O título do PR segue o mesmo formato (é validado no CI).

## Definição de Pronto

Uma issue só está pronta quando (é o mesmo checklist do template de PR):

- [ ] Critérios de aceite da issue atendidos
- [ ] Testes escritos e passando; cobertura não diminuiu
- [ ] Lint, formatação e tipos sem erros (`pre-commit`)
- [ ] Sem code smells (checklist abaixo)
- [ ] Documentação, diagramas e `.env.example` atualizados (se aplicável)
- [ ] ADR criado (se a decisão for difícil de reverter)
- [ ] Sem segredos ou dados pessoais em código e logs
- [ ] `CHANGELOG.md` atualizado (seção *Não lançado*)
- [ ] PR revisado e aprovado; CI verde
- [ ] Deploy em staging verificado (quando houver staging)

### Code smells ([Refactoring Guru](https://refactoring.guru/pt-br/refactoring/smells))

- [ ] Sem métodos longos (> 50 linhas) ou classes grandes
- [ ] Sem código duplicado
- [ ] Sem obsessão por primitivos (unidades e dinheiro com tipos próprios / `Decimal`)
- [ ] Sem lista longa de parâmetros
- [ ] Regra de negócio fora das rotas e dos componentes de tela

## Ferramentas locais

```bash
pip install pre-commit
pre-commit install --hook-type pre-commit --hook-type commit-msg
pre-commit run --all-files
```

## Versionamento

Usamos [SemVer](https://semver.org/lang/pt-BR/): `MAJOR.MINOR.PATCH`.
Cada release gera uma tag `vX.Y.Z` e move as entradas do `CHANGELOG.md` de *Não lançado* para a versão.
