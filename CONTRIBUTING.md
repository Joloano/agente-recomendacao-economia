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
7. **Merge** só com CI verde. A branch é apagada após o merge.

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

## Definição de Pronto (DoD)

Uma issue só está pronta quando:

- [ ] Critérios de aceite da issue atendidos
- [ ] Testes escritos e passando; cobertura não diminuiu
- [ ] Lint, formatação e tipos sem erros (`pre-commit`)
- [ ] Sem code smells evidentes (veja o checklist do PR)
- [ ] Documentação, diagramas e `.env.example` atualizados quando necessário
- [ ] ADR criado se a decisão for difícil de reverter
- [ ] Nenhum segredo ou dado pessoal no código ou nos logs
- [ ] PR revisado e aprovado; CI verde
- [ ] `CHANGELOG.md` atualizado (seção *Não lançado*)

## Ferramentas locais

```bash
pip install pre-commit
pre-commit install --hook-type pre-commit --hook-type commit-msg
pre-commit run --all-files
```

## Versionamento

Usamos [SemVer](https://semver.org/lang/pt-BR/): `MAJOR.MINOR.PATCH`.
Cada release gera uma tag `vX.Y.Z` e move as entradas do `CHANGELOG.md` de *Não lançado* para a versão.
