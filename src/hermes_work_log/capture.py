"""Captura de linguagem natural -> Atividade do hermes-core.

Orquestra: interpreter -> draft -> factory -> Store.
A única entidade persistida é Atividade (do Core). Work Log não cria
entidade de domínio própria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from hermes_core import Atividade
from hermes_core.store import Store

from .interpreter import (
    AtividadeDraft,
    CaptureContext,
    DeterministicInterpreter,
    Interpreter,
)


@dataclass
class CampoInferido:
    """Sugestão de referência que NÃO será persistida como fato sem confirmação."""

    campo: str
    sugestao: str  # nome textual, não ID


@dataclass
class PendenteConfirmacao:
    """Retornado quando há informação inferred relevante.

    A Atividade é construída apenas com campos seguros (provided/derived).
    As sugestões ficam aqui para o canal de entrada confirmar.
    """

    atividade: Atividade
    sugestoes: list[CampoInferido] = field(default_factory=list)


def _build_atividade(draft: AtividadeDraft, owner_id: Optional[str] = None,
                     contexto: Optional["CaptureContext"] = None) -> Atividade:
    """Factory puro: Draft -> Atividade do Core (apenas campos seguros).

    Contexto explícito do caller (projeto_id/tarefa_id) tem precedência e é
    repassado; o Core valida a estrutura do ID. Não gera nem resolve IDs.
    """
    kwargs: dict = {
        "descricao": draft.descricao.valor,
        "ocorrido_em": draft.ocorrido_em.valor,
    }
    if owner_id:
        kwargs["owner_id"] = owner_id
    if contexto is not None:
        if contexto.projeto_id:
            kwargs["projeto_id"] = contexto.projeto_id
        if contexto.tarefa_id:
            kwargs["tarefa_id"] = contexto.tarefa_id

    # tech/repo: só se derived (não geramos IDs inventados; nomes como 'python'
    # são apenas rótulos — mas o Core exige IDs. V1 NÃO persiste refs inventadas.
    # Mantemos listas vazias para referências resolvidas em evolução futura.
    # tech_ids/repo_ids/documentos permanecem vazios até resolução por nome.
    return Atividade(**kwargs)


def capturar(
    texto: str,
    contexto: Optional[CaptureContext] = None,
    interpreter: Optional[Interpreter] = None,
    store: Optional[Store] = None,
    owner_id: Optional[str] = None,
) -> Atividade | PendenteConfirmacao:
    """Ponto de entrada único do Work Log.

    texto -> interpreter -> draft -> factory -> (Store)
    Retorna Atividade (persistida se store dado) ou PendenteConfirmacao.
    """
    interp = interpreter or DeterministicInterpreter()
    draft = interp.interpret(texto, contexto)

    sugestoes: list[CampoInferido] = []
    if draft.projeto_sugerido:
        sugestoes.append(CampoInferido("projeto", draft.projeto_sugerido))
    if draft.tarefa_sugerida:
        sugestoes.append(CampoInferido("tarefa", draft.tarefa_sugerida))

    atividade = _build_atividade(draft, owner_id=owner_id, contexto=contexto)

    if sugestoes:
        return PendenteConfirmacao(atividade=atividade, sugestoes=sugestoes)

    if store is not None:
        store.put(atividade)
    return atividade
