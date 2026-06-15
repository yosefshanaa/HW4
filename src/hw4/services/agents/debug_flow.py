"""Graph-guided debugging agent flow (EX04 §5.3) — locate, then explain.

Mirrors analyze_flow's deterministic-spine discipline: the graph LOCALIZES
the defect (the failing test's `tested_by` edge names one module — no
full-tree read), and the CrewAI analyst then receives ONLY that module's
source and explains the root cause + names the fix. The context-reduction
mechanism is the point: graph first, one snippet on demand, never the
whole package. Every agent call is gated and ledger-tagged `agent.analyst`.
"""

from __future__ import annotations

from pathlib import Path

from hw4.services.agents.context import pack
from hw4.services.agents.roles import make_agent
from hw4.services.debug import run_debug_case
from hw4.shared.gatekeeper import BudgetExceededError

DEBUG_RULES = (
    "You are debugging ONE localized module. Rely on the graph localization and "
    "the single source snippet you are given — do not ask for other files. "
    "Explain the root cause precisely, cite the function and the exact line, and "
    "name the one-line fix; qualify any uncertainty."
)


def debug_flow(sdk, root) -> dict:
    """Localize via the graph, hand the analyst ONLY that module, explain the bug."""
    result = run_debug_case(root, sdk.config)
    module_file = Path(root) / (result.located_module.replace(".", "/") + ".py")
    snippet = module_file.read_text(encoding="utf-8")
    analyst = make_agent("analyst", sdk.llm)
    prompt = pack(
        DEBUG_RULES,
        f"Symptom: parse_byte_range for {result.case} returns {result.buggy_value}, "
        f"expected {result.expected}.\n"
        f"The graph localized the defect to `{result.located_module}` via the failing "
        f"test's tested_by edge, so we read ONLY this module "
        f"({result.graph_tokens} tok vs {result.naive_tokens} for the whole package):\n"
        f"```python\n{snippet}```",
        "Explain the root cause in 3 careful sentences and name the one-line fix.",
    )
    try:
        narrative = analyst.llm.call(prompt)
    except BudgetExceededError as exc:
        return {"located_module": result.located_module, "narrative_path": "",
                "halted": f"budget firewall: {exc}"}
    out = sdk.results_dir / "agent_debug.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "# Graph-guided debug — CrewAI analyst narrative\n\n"
        f"Localized via the graph `tested_by` edge: **`{result.located_module}`** · "
        f"context {result.graph_tokens} tok (snippet only) vs {result.naive_tokens} tok "
        f"(whole package).\n\n{narrative}\n",
        encoding="utf-8",
    )
    return {"located_module": result.located_module,
            "narrative_path": str(out), "narrative": narrative, "halted": ""}
