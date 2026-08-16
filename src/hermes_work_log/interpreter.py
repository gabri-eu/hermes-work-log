"""Interpretação de linguagem natural em Draft transitório.

O Interpreter é uma abstração (Protocol). A V1 usa implementação
determinística, sem LLM e sem rede. Um futuro LLMInterpreter implementa
o mesmo contrato, sem provider de LLM no domínio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Protocol


class Provenance(str, Enum):
    """Origem do valor de um campo.

    provided = dito explicitamente pelo usuário.
    derived  = determinado de forma mecânica a partir de texto/contexto
               (ex.: "hoje" -> data corrente).
    inferred = depende de interpretação/hipótese do agente
               (ex.: qual Projeto existente o usuário quis dizer).
    """

    PROVIDED = "provided"
    DERIVED = "derived"
    INFERRED = "inferred"


@dataclass
class Campo:
    """Valor de um campo com sua provenance. DTO puro, sem lógica."""

    valor: object
    provenance: Provenance


@dataclass
class AtividadeDraft:
    """DTO transitório entre interpreter e validação/factory.

    NÃO é entidade de domínio, NÃO é persistido. Apenas carrega os campos
    necessários para construir uma Atividade do Core, com provenance por
    campo para a política de confirmação.
    """

    descricao: Campo
    ocorrido_em: Campo
    projeto_sugerido: Optional[str] = None  # nome textual, NUNCA proj_... inventado
    tarefa_sugerida: Optional[str] = None
    tech_ids: list[Campo] = field(default_factory=list)
    doc_ids: list[Campo] = field(default_factory=list)
    repo_ids: list[Campo] = field(default_factory=list)


class CaptureContext:
    """Contexto útil para interpretar a captura.

    Não contém conceitos de canais de mensageria, almoço, fim de expediente
    ou scheduler. Apenas o que ajuda a interpretar o momento/referências.
    """

    def __init__(
        self,
        ocorrido_em: Optional[datetime] = None,
        projeto_id: Optional[str] = None,
        tarefa_id: Optional[str] = None,
    ) -> None:
        self.ocorrido_em = ocorrido_em
        self.projeto_id = projeto_id
        self.tarefa_id = tarefa_id


class Interpreter(Protocol):
    """Contrato de interpretação. Implementações: determinística (V1), LLM (futuro)."""

    def interpret(
        self, texto: str, contexto: Optional[CaptureContext] = None
    ) -> AtividadeDraft: ...


class DeterministicInterpreter:
    """Interpreter V1: heurísticas simples, sem rede, sem LLM.

    - descrição: o próprio texto (provided).
    - ocorrido_em: contexto se houver, senão data corrente (derived).
    - menções de tech/repo por padrões mínimos: derived quando casam.
    - projeto/tarefa mencionados por nome: sugestão textual (inferred),
      jamais geração de ID.
    """

    _TECH_PATTERNS = {
        "python": "python",
        "airflow": "airflow",
        "dbt": "dbt",
        "sql": "sql",
        "api": "api",
        "dag": "dag",
    }
    _REPO_PATTERNS = {
        "github": "github",
        "gitlab": "gitlab",
    }

    def interpret(
        self, texto: str, contexto: Optional[CaptureContext] = None
    ) -> AtividadeDraft:
        ctx = contexto or CaptureContext()

        # ocorrido_em: contexto (provided se veio do usuário) ou derived (hoje)
        if ctx.ocorrido_em is not None:
            ocorrido = Campo(ctx.ocorrido_em, Provenance.PROVIDED)
        else:
            ocorrido = Campo(datetime.now(), Provenance.DERIVED)

        descricao = Campo(texto.strip(), Provenance.PROVIDED)

        tech_ids: list[Campo] = []
        low = texto.lower()
        for padrao, nome in self._TECH_PATTERNS.items():
            if padrao in low:
                tech_ids.append(Campo(nome, Provenance.DERIVED))

        repo_ids: list[Campo] = []
        for padrao, nome in self._REPO_PATTERNS.items():
            if padrao in low:
                repo_ids.append(Campo(nome, Provenance.DERIVED))

        # projeto/tarefa por nome = inferred (sugestão textual, sem ID)
        projeto_sugerido = self._sugerir_nome(texto, "projeto")
        tarefa_sugerida = self._sugerir_nome(texto, "tarefa")

        return AtividadeDraft(
            descricao=descricao,
            ocorrido_em=ocorrido,
            projeto_sugerido=projeto_sugerido,
            tarefa_sugerida=tarefa_sugerida,
            tech_ids=tech_ids,
            repo_ids=repo_ids,
        )

    @staticmethod
    def _sugerir_nome(texto: str, rotulo: str) -> Optional[str]:
        """Extrai 'no <rotulo> Nome' como sugestão textual (inferred).

        Coleta palavras após o rótulo até uma palavra de parada ou pontuação.
        """
        import re

        m = re.search(rf"\b{rotulo}\b", texto, re.IGNORECASE)
        if not m:
            return None
        resto = texto[m.end():].strip()
        if not resto:
            return None
        stopwords = {
            "usei", "usamos", "usou", "e", "com", "fiz", "fizemos", "fez",
            "revisei", "revise", "corrigi", "corrigiu", "no", "na", "para",
            "que", "onde", "mas", "apos", "depois",
        }
        tokens = re.findall(r"[\wÀ-ÿ\-]+", resto)
        coletados: list[str] = []
        for tok in tokens:
            if tok.lower() in stopwords:
                break
            coletados.append(tok)
            if len(coletados) >= 4:
                break
        return " ".join(coletados) if coletados else None
