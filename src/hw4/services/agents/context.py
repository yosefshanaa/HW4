"""Agent context packing + history compaction (T299-T300, FR-5.5).

Edge placement (Part-B): critical rules FIRST, the task LAST, payload in
the middle. Compaction keeps the rules block VERBATIM — rules that only
survive as a summary stop being rules — and lets the LLM (purpose tag
`compact`, cheap tier) summarize only the history between them.
"""

from __future__ import annotations

from hw4.constants import ModelTier
from hw4.services.retrieval import estimate_tokens
from hw4.shared.llm_client import LlmClient

COMPACT_SYSTEM = (
    "Summarize the following agent interaction history into at most 10 bullet "
    "lines. Keep finding ids, file paths, verdicts and numbers exact. Drop "
    "pleasantries and repetition. Respond with the bullets only."
)


def pack(rules: str, payload: str, task: str) -> str:
    """instructions/rules FIRST, task LAST — position-aware by design."""
    return f"{rules}\n\n## Working material\n{payload}\n\n## Task\n{task}"


def compact_history(llm: LlmClient, rules: str, history: list[str]) -> tuple[str, dict]:
    """Compress history between iterations; rules survive verbatim.

    Returns (new context block, stats with before/after token estimates).
    """
    joined = "\n".join(history)
    before = estimate_tokens(pack(rules, joined, ""))
    response = llm.complete(
        [{"role": "user", "content": joined}],
        purpose_tag="compact",
        tier=ModelTier.CHEAP,
        system=COMPACT_SYSTEM,
    )
    compacted = pack(rules, response.text, "")
    after = estimate_tokens(compacted)
    return compacted, {
        "tokens_before": before,
        "tokens_after": after,
        "reduction": round(1 - after / before, 4) if before else 0.0,
    }
