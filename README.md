# hermes-work-log

Produto independente do ecossistema Hermes para **captura rápida** do que o
usuário fez, transformando linguagem natural em `Atividade` do
[hermes-core](https://github.com/gabri-eu/hermes-core).

## Princípios

- Work Log é um **workflow de captura**, não uma entidade de domínio.
- A entidade persistida é `Atividade` (definida pelo Core).
- Depende apenas do `hermes-core`.
- V1 sem LLM real: `Interpreter` é um `Protocol`; a implementação é
  determinística. Um futuro `LLMInterpreter` respeita o mesmo contrato.
- Informação `inferred` não vira fato sem confirmação (human-in-the-loop).

## Uso

```python
from hermes_work_log import capturar
from hermes_core.store import InMemoryStore

store = InMemoryStore()
resultado = capturar("Hoje corrigi a DAG de processamento.", store=store)
# -> Atividade (se não houver inferência) ou PendenteConfirmacao
```

## Fora de escopo (V1)

Telegram, Dashboard, Obsidian, Knowledge, Publicações, Data Engineering,
GitHub integration, RAG, banco de dados, LLM real.

## Dependência

`hermes-core` (pin por commit `418a230…`):
`git+ssh://git@github.com/gabri-eu/hermes-core.git@418a23047a4bc2042e6779df95a9cf5f205716a5`
