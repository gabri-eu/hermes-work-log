"""Testes do hermes-work-log (V1, sem LLM real)."""

import pytest
from datetime import datetime

from hermes_core import Atividade, new_id
from hermes_core.store import InMemoryStore

from hermes_work_log import (
    AtividadeDraft,
    CaptureContext,
    DeterministicInterpreter,
    PendenteConfirmacao,
    Provenance,
    capturar,
)


def _interp():
    return DeterministicInterpreter()


# 1. captura mínima -------------------------------------------------------
def test_captura_minima():
    a = capturar("Hoje corrigi a DAG de processamento.")
    assert isinstance(a, Atividade)
    assert a.descricao == "Hoje corrigi a DAG de processamento."
    assert a.ocorrido_em is not None


# 2. ocorrido_em explícito ------------------------------------------------
def test_ocorrido_em_explicito():
    momento = datetime(2026, 8, 16, 14, 30)
    ctx = CaptureContext(ocorrido_em=momento)
    a = capturar("Adaptei a DAG", contexto=ctx)
    assert isinstance(a, Atividade)
    assert a.ocorrido_em == momento


# 3. fallback temporal ---------------------------------------------------
def test_fallback_temporal():
    a = capturar("Qualquer coisa")
    assert isinstance(a, Atividade)
    assert isinstance(a.ocorrido_em, datetime)


# 4. distinção criado_em / ocorrido_em -----------------------------------
def test_distincao_criado_ocorrido():
    momento = datetime(2026, 1, 1, 9, 0)
    ctx = CaptureContext(ocorrido_em=momento)
    a = capturar("Trabalhei no passado", contexto=ctx)
    assert a.ocorrido_em == momento
    assert a.criado_em >= momento


# 5. provided ------------------------------------------------------------
def test_provenance_provided():
    d = _interp().interpret("Mensagem qualquer")
    assert d.descricao.provenance == Provenance.PROVIDED
    assert d.ocorrido_em.provenance == Provenance.DERIVED


# 6. derived -------------------------------------------------------------
def test_provenance_derived_explicito():
    momento = datetime(2026, 8, 16, 10, 0)
    d = _interp().interpret("x")
    d2 = _interp().interpret("x", contexto=CaptureContext(ocorrido_em=momento))
    assert d2.ocorrido_em.provenance == Provenance.PROVIDED
    assert d.ocorrido_em.provenance == Provenance.DERIVED


# 7. inferred ------------------------------------------------------------
def test_provenance_inferred_projeto():
    d = _interp().interpret("Trabalhei no projeto Adaptação DAG Exemplo")
    assert d.projeto_sugerido == "Adaptação DAG Exemplo"
    res = capturar("Trabalhei no projeto Adaptação DAG Exemplo")
    assert isinstance(res, PendenteConfirmacao)
    assert res.sugestoes[0].campo == "projeto"


# 8. rejeição de IDs inválidos (pelo Core) -------------------------------
def test_ids_invalidos_rejeitados_pelo_core():
    with pytest.raises(Exception):
        capturar("x", owner_id="pessoa_invalida")


# 9. não geração de IDs de referência inexistentes -----------------------
def test_nao_gera_ids_referencia():
    d = _interp().interpret("No projeto X usei python e github")
    assert all(
        not str(c.valor).startswith(("proj_", "task_", "tech_", "repo_"))
        for c in d.tech_ids + d.repo_ids
    )
    assert d.projeto_sugerido == "X"


# 10. criação correta de Atividade --------------------------------------
def test_atividade_correta():
    a = capturar("Corrigi drift de schema")
    assert isinstance(a, Atividade)
    assert a.tipo == "atividade"
    assert a.id.startswith("act_")


# 11. PendenteConfirmacao ------------------------------------------------
def test_pendente_confirmacao():
    res = capturar("No projeto X revisei o código")
    assert isinstance(res, PendenteConfirmacao)
    assert isinstance(res.atividade, Atividade)
    assert res.atividade.projeto_id is None


# 11b. CaptureContext.projeto_id válido chega à Atividade ----------------
def test_contexto_projeto_id_aplicado():
    ctx = CaptureContext(projeto_id=new_id("proj"))
    a = capturar("Trabalhei", contexto=ctx)
    assert isinstance(a, Atividade)
    assert a.projeto_id == ctx.projeto_id


def test_contexto_tarefa_id_aplicado():
    ctx = CaptureContext(tarefa_id=new_id("task"))
    a = capturar("Trabalhei", contexto=ctx)
    assert isinstance(a, Atividade)
    assert a.tarefa_id == ctx.tarefa_id


def test_contexto_projeto_id_invalido_rejeitado():
    ctx = CaptureContext(projeto_id="projeto_invalido")
    with pytest.raises(Exception):
        capturar("Trabalhei", contexto=ctx)


def test_contexto_tarefa_id_invalido_rejeitado():
    ctx = CaptureContext(tarefa_id="task_xxx")
    with pytest.raises(Exception):
        capturar("Trabalhei", contexto=ctx)


def test_contexto_ambos_aplicados():
    ctx = CaptureContext(projeto_id=new_id("proj"), tarefa_id=new_id("task"))
    a = capturar("Trabalhei", contexto=ctx)
    assert isinstance(a, Atividade)
    assert a.projeto_id == ctx.projeto_id
    assert a.tarefa_id == ctx.tarefa_id


# 12. persistência através do Store --------------------------------------
def test_persistencia_store():
    store = InMemoryStore()
    a = capturar("Atividade simples", store=store)
    assert isinstance(a, Atividade)
    assert store.get(a.id).descricao == "Atividade simples"


def test_persistencia_store_com_inferred_fica_pendente():
    store = InMemoryStore()
    res = capturar("No projeto Y fiz algo", store=store)
    assert isinstance(res, PendenteConfirmacao)
    assert store.get(res.atividade.id) is None


# 13. funcionamento sem LLM ---------------------------------------------
def test_sem_llm():
    a = capturar("Texto qualquer sem LLM")
    assert isinstance(a, Atividade)


# 14. ausência de dependências indevidas --------------------------------
def test_sem_acoplamento_externo():
    import pathlib

    src_files = [
        "src/hermes_work_log/capture.py",
        "src/hermes_work_log/interpreter.py",
        "src/hermes_work_log/__init__.py",
    ]
    for f in src_files:
        texto = pathlib.Path(f).read_text()
        for termo in ("telegram", "obsidian", "knowledge", "publication",
                      "data_engineering", "sqlite", "openai", "anthropic"):
            assert termo.lower() not in texto.lower(), f"{termo} em {f}"


def test_dependencia_externa_core():
    import hermes_core

    assert hasattr(hermes_core, "Atividade")
