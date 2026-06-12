"""Crew wiring + the analyze flow (T301-T304, PLAN §3.1).

Design stance executed literally: everything computable without an LLM
(graph build, detectors) runs as plain tool calls; the LLM appears only
where judgment lives — the analyst's careful-language narrative. The
deterministic spine guarantees findings.json equals the direct-SDK path
byte-for-byte; agents add interpretation, never facts.

`build_crew` assembles a real CrewAI Crew (for the live kickoff demo);
`analyze_flow` is the auditable orchestration used by tests and CI.
"""

from __future__ import annotations

from crewai import Crew, Task

from hw4.services.agents import tools
from hw4.services.agents.context import pack
from hw4.services.agents.payloads import AnalysisRequest
from hw4.services.agents.roles import make_agent
from hw4.shared.gatekeeper import BudgetExceededError

ANALYST_RULES = (
    "Rules (non-negotiable): qualify every claim to its evidence class; use "
    "'suggests'/'appears to' for INFERRED, flag AMBIGUOUS for human check; cite "
    "node ids and source files; never recommend deletion from similarity alone."
)


def analyst_rules(sdk) -> str:
    """ANALYST_RULES + the SKILL procedure verbatim (T398, anti-drift)."""
    skill = sdk.base_dir / "docs" / "SKILL.md"
    if not skill.exists():
        return ANALYST_RULES
    text = skill.read_text(encoding="utf-8")
    if "## Procedure" not in text:
        return ANALYST_RULES
    procedure = text.split("## Procedure", 1)[1].split("\n## ", 1)[0]
    return f"{ANALYST_RULES}\n\nSkill procedure (reloaded fresh):{procedure}"


def build_crew(sdk) -> Crew:
    """A real CrewAI crew for the live demo path (kickoff needs an API key)."""
    repo_agent = make_agent("repo", sdk.llm)
    analyst = make_agent("analyst", sdk.llm)
    graph_task = Task(
        description="Build the next immutable graph iteration for the target repo.",
        expected_output="iteration number + content hash",
        agent=repo_agent,
    )
    analysis_task = Task(
        description="Run detectors and write evidence-chained finding narratives.",
        expected_output="ranked findings with careful-language narratives",
        agent=analyst,
    )
    return Crew(agents=[repo_agent, analyst], tasks=[graph_task, analysis_task])


def analyze_flow(sdk, request: AnalysisRequest) -> dict:
    """Repo -> Analyst flow with a deterministic spine (T301/T302)."""
    trace: list[dict] = []
    analyst = make_agent("analyst", sdk.llm)

    graph_info = tools.assert_serializable(
        tools.build_graph(sdk, request.repo_path, iteration=request.iteration)
    )
    trace.append({"step": "repo.build_graph", "result": graph_info})

    detection = tools.assert_serializable(tools.run_detectors(sdk))
    trace.append({"step": "analyst.run_detectors", "result": {"count": detection["count"]}})

    narratives, halted = [], ""
    rules = analyst_rules(sdk)
    for finding in detection["findings"][: request.narrative_top_n]:
        prompt = pack(
            rules,
            f"Finding {finding['id']} ({finding['kind']}, confidence "
            f"{finding['confidence']}):\n{finding['evidence_chain']}",
            "Write a 3-sentence careful-language narrative for this finding.",
        )
        try:
            narratives.append(f"## {finding['id']}\n{analyst.llm.call(prompt)}")
        except BudgetExceededError as exc:
            halted = f"budget firewall: {exc}"
            break
    narrative_path = ""
    if narratives:
        out = sdk.results_dir / "agent_analysis.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n\n".join(narratives), encoding="utf-8")
        narrative_path = str(out)
    trace.append({"step": "analyst.narratives", "result": {"written": len(narratives)}})

    return {
        "trace": trace,
        "iteration": graph_info["iteration"],
        "findings_count": detection["count"],
        "narrative_path": narrative_path,
        "halted": halted,
    }
