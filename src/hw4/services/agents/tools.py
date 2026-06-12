"""Agent tools — thin SDK delegates, zero logic (T295-T296, FR-5.4).

Every tool takes the facade and returns a JSON-serializable dict; the
SDK (and therefore the Gatekeeper) does all the work. A tool that grew
an if-statement of business logic would be a layering bug.
"""

from __future__ import annotations

import json
from pathlib import Path


def build_graph(sdk, repo_path: str, iteration: int | None = None) -> dict:
    record = sdk.build_graph(repo_path, iteration=iteration)
    return {
        "iteration": record.iteration,
        "graph_path": str(record.graph_path),
        "content_hash": record.content_hash,
        "nodes": record.nodes,
        "edges": record.edges,
    }


def run_detectors(sdk, graph_path: str | None = None) -> dict:
    findings = sdk.analyze(graph_path)
    return {
        "count": len(findings),
        "findings": [finding.to_dict() for finding in findings],
    }


def retrieve_context(sdk, question: str) -> dict:
    result = sdk.ask(question)
    return {
        "answer": result.answer,
        "matched_nodes": result.matched_nodes,
        "source_files": result.source_files,
        "context_token_estimate": result.context_token_estimate,
    }


def run_fix_loop(sdk, finding_id: str = "", auto: bool = False) -> dict:
    return sdk.fix(finding_id, auto=auto)


def ledger_status(sdk) -> dict:
    return sdk.ledger.totals()


def assert_serializable(payload: dict) -> dict:
    """Guard used in tests and at tool boundaries: handoffs must be JSON."""
    json.dumps(payload)
    return payload


def read_artifact(sdk, relative_path: str) -> dict:
    """Read one results/ artifact (audit access for QA), path-jailed."""
    base = Path(sdk.results_dir).resolve()
    target = (base / relative_path).resolve()
    if not str(target).startswith(str(base)):
        raise PermissionError("artifact access outside results/ is not allowed")
    return {"path": relative_path, "content": target.read_text(encoding="utf-8")}
