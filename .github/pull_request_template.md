## Problema
<!-- O que motivou a mudança? -->

## Solução
<!-- O que foi feito e por quê. Decisões relevantes. -->

## Como verificar
<!-- Comandos, telas ou rotas para conferir. -->

Closes #

## Definição de Pronto
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

## Code smells (Refactoring Guru)
- [ ] Sem métodos longos (> 50 linhas) ou classes grandes
- [ ] Sem código duplicado
- [ ] Sem obsessão por primitivos (unidades e dinheiro com tipos próprios / `Decimal`)
- [ ] Sem lista longa de parâmetros
- [ ] Regra de negócio fora das rotas e dos componentes de tela
