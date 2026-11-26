# ADR 0001 — Arquitetura em camadas com domínio puro

- **Situação:** aceita
- **Data:** 2026-11-25
- **Issues:** #32, #114

## Contexto

O agente original era um script único em que leitura do CSV, regras, cálculo e interação no
terminal estavam misturados. O produto precisa expor o mesmo agente por API REST, assistentes de
voz e, no futuro, automações da casa, com dados no PostgreSQL. Precisamos testar as regras sem
banco e trocar a forma de entrada/saída sem reescrever o agente.

## Decisão

Separar o backend em camadas: **api** (rotas FastAPI finas) → **services** (casos de uso) →
**agente** (domínio em Python puro) e **repositórios** (SQLAlchemy). O domínio não importa nada de
infraestrutura. Variações por recurso usam Strategy + Template Method + Factory Method; as regras de
elegibilidade, Chain of Responsibility; o acesso externo ao agente, uma Facade. Detalhes em
[padrões de projeto](../padroes-de-projeto.md).

Quantidades e dinheiro usam `Decimal`. O comportamento do script original é garantido por testes
de regressão que comparam as dez residências do dataset.

## Alternativas consideradas

- **Manter funções soltas como no script**: simples, mas sem ponto de extensão para água e sem
  isolamento para testes.
- **Regras dentro dos modelos SQLAlchemy**: acopla o domínio ao banco e torna os testes lentos.

## Consequências

- ✅ Regras testáveis em milissegundos, sem banco.
- ✅ Novo recurso (água, gás) exige só uma nova estratégia registrada.
- ⚠️ Mais arquivos e conversões entre modelos do banco e objetos de domínio.
