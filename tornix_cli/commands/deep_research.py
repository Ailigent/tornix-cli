from __future__ import annotations

from typing import Any

import click

from ..client import TornixClient
from ..output import emit

# PMO sections to gather. "{project}" templates are project-nested; flat paths
# accept a project_id query filter when a project is given.
_PMO_SECTIONS = [
    ("tasks", "/api/v1/projects/{project}/tasks", "id"),
    ("risks", "/api/v1/projects/{project}/risks", "id"),
    ("approvals", "/api/v1/approvals/requests", "id"),
    ("meetings", "/api/v1/meetings", "id"),
    ("documents", "/api/v1/documents", "id"),
]


def _cite(kind: str, item: dict, field: str) -> str:
    return f"tornix://{kind}/{item.get(field)}"


def assemble_pmo_corpus(client: TornixClient, *, project_id: str | None = None,
                        portfolio_id: str | None = None) -> dict:
    project = None
    if project_id:
        project = client.get(f"/api/v1/projects/{project_id}")
    sections: list[dict] = []
    for kind, tmpl, cite_field in _PMO_SECTIONS:
        if "{project}" in tmpl:
            if not project_id:
                continue
            path = tmpl.replace("{project}", project_id)
            params = None
        else:
            path = tmpl
            params = {"project_id": project_id} if project_id else None
        try:
            rows = client.get(path, params=params) or []
        except Exception:
            rows = []
        if not isinstance(rows, list):
            rows = [rows]
        items = [{**r, "citation": _cite(kind, r, cite_field)} for r in rows if isinstance(r, dict)]
        if items:
            sections.append({"kind": kind, "count": len(items), "items": items})
    return {"project": project, "portfolio_id": portfolio_id, "sections": sections}


def _decompose(question: str) -> list[str]:
    """Heuristic sub-questions; the driving agent refines these."""
    return [
        f"What direct evidence in the PMO data addresses: {question}",
        "Which tasks/risks/approvals are blocking or delayed?",
        "What do recent meetings and documents say about the cause?",
        "What corrective actions are implied by the evidence?",
    ]


@click.command(name="deep-research",
               help="Multi-source research over PMO data and/or the web.")
@click.argument("question")
@click.option("--source", type=click.Choice(["pmo", "web", "both"]), default="pmo")
@click.option("--project", "project_id", default=None)
@click.option("--portfolio", "portfolio_id", default=None)
@click.option("--synthesize", is_flag=True,
              help="Standalone: call Tornix AI to write the final report (uses credits).")
@click.pass_obj
def deep_research_command(obj, question, source, project_id, portfolio_id, synthesize):
    client: TornixClient = obj["client"]
    json_mode = obj.get("json", True)

    corpus: dict[str, Any] = {}
    if source in ("pmo", "both"):
        corpus = assemble_pmo_corpus(client, project_id=project_id, portfolio_id=portfolio_id)

    web_brief = None
    if source in ("web", "both"):
        web_brief = {"search_queries": _decompose(question),
                     "note": "Web execution is delegated to the driving agent's tools "
                             "(or --synthesize uses the configured provider)."}

    if synthesize:
        # Standalone synthesis via the AI proxy (credit-metered). The generate-chat
        # endpoint is a concrete public AI entry point; pass the corpus as context.
        prompt = (f"Question: {question}\n\nUsing only the supplied Tornix PMO corpus and "
                  f"web findings, write a concise, cited report. Cite PMO facts by their "
                  f"`citation` (tornix://kind/id) and web facts by URL.")
        payload = {"messages": [{"role": "user", "content": prompt}],
                   "context": {"question": question, "source": source,
                               "corpus": corpus, "web_brief": web_brief}}
        report = client.post("/api/v1/ai/generate-chat", json=payload)
        emit({"mode": "synthesize", "question": question, "report": report},
             json_mode=json_mode)
        return

    emit({"mode": "agent", "question": question, "source": source,
          "sub_questions": _decompose(question), "corpus": corpus,
          "web_brief": web_brief,
          "instructions": "Synthesize a cited answer. Cite PMO facts by their "
                          "`citation` (tornix://kind/id); cite web facts by URL."},
         json_mode=json_mode)
