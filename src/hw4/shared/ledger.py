"""Append-only token/cost ledger — the evidence base for FR-8 and §11.

Every LLM call writes one JSONL row tagged with a purpose (experiment.A,
fixloop.iter2, wiki.gen ...). The token experiment, the cost analysis, and
the budget firewall are all just aggregations over this file — one source
of truth instead of three bookkeeping systems.
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from hw4.shared.config import Config


@dataclass(frozen=True)
class LedgerEntry:
    """One recorded external LLM call."""

    ts: str
    purpose_tag: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    status: str


class Ledger:
    """JSONL-backed ledger with config-driven pricing (prices are config)."""

    def __init__(self, config: Config, path: Path | str):
        self._pricing = config.get("pricing_per_mtok", default={})
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Parallel wiki/agent calls record concurrently (§15): the append and
        # the read-back must not interleave into a torn JSONL line.
        self._lock = threading.Lock()

    def cost_of(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Cost in USD from the per-million-token price table in setup.json."""
        prices = self._pricing.get(model)
        if prices is None:
            return 0.0  # unknown model: recorded, priced as zero, visible in audit
        cost = (
            input_tokens * prices["input"] + output_tokens * prices["output"]
        ) / 1_000_000
        return round(cost, 6)

    def record(
        self,
        *,
        purpose_tag: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        status: str = "ok",
    ) -> LedgerEntry:
        """Append one call; returns the entry including computed cost."""
        entry = LedgerEntry(
            ts=datetime.now(timezone.utc).isoformat(),
            purpose_tag=purpose_tag,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self.cost_of(model, input_tokens, output_tokens),
            latency_ms=latency_ms,
            status=status,
        )
        with self._lock, self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(entry)) + "\n")
        return entry

    def entries(self) -> list[LedgerEntry]:
        """Read back all rows (used by totals, the notebook, and tests)."""
        with self._lock:
            if not self._path.is_file():
                return []
            raw = self._path.read_text(encoding="utf-8")
        rows = []
        for line in raw.splitlines():
            if line.strip():
                rows.append(LedgerEntry(**json.loads(line)))
        return rows

    def totals(self, purpose_prefix: str = "") -> dict[str, float]:
        """Aggregate tokens/cost for entries whose tag starts with the prefix."""
        selected = [e for e in self.entries() if e.purpose_tag.startswith(purpose_prefix)]
        return {
            "calls": len(selected),
            "input_tokens": sum(e.input_tokens for e in selected),
            "output_tokens": sum(e.output_tokens for e in selected),
            "cost_usd": round(sum(e.cost_usd for e in selected), 6),
        }

    def total_cost(self) -> float:
        """Cumulative spend — the number the budget firewall checks."""
        return self.totals()["cost_usd"]
