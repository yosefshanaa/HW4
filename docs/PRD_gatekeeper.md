# PRD — API Gatekeeper & Token Ledger

**Status:** approved 2026-06-12 (as-built: `src/hw4/shared/gatekeeper.py`, `ledger.py`, `llm_client.py`) ·
**Serves:** NFR-2, FR-5.4, guidelines §5 · **Parent:** PRD.md, PLAN §1.2

## 1. Description & theory

Every external call (LLM API today; any future service) passes through one
choke point, `ApiGatekeeper.execute`. One choke point yields four system
properties *for free everywhere*, instead of asking each caller for
discipline:

1. **Rate limiting** — sliding per-minute and per-hour windows (deques of
   monotonic timestamps), limits from `config/rate_limits.json`.
2. **Queue, never drop** — on saturation the request waits FIFO until the
   oldest timestamp leaves the window; agents upstream never see a dropped
   call, only latency.
3. **Bounded retries** — `TransientApiError` (HTTP 408/409/429/5xx/529,
   connection failures — mapped by the transport) retried up to
   `max_retries` with `retry_after_seconds` backoff; then
   `RetriesExhaustedError`.
4. **Budget firewall + audit** — before any call, cumulative ledger cost is
   checked against `budget.max_usd` (`BudgetExceededError` hard-stops
   runaway agent loops); after any call, one JSONL ledger row records
   purpose tag, model, tokens, cost, latency, status.

Token counts come from **provider API usage metadata**, never a local
tokenizer — the token experiment's numbers must be ground truth (PLAN §4.4).

## 2. Interfaces & I/O

```python
gate = ApiGatekeeper(config, ledger, service="default", clock=..., sleeper=...)
value = gate.execute(call, *, purpose_tag="experiment.B.q2", model="...")
# call: () -> CallResult(value, input_tokens, output_tokens)
gate.get_queue_status()  # -> QueueStatus(waits, total_wait_seconds, windows used)
```

- **In:** zero-arg callable returning `CallResult`; purpose tag (dotted,
  e.g. `wiki.page.<node>`, `experiment.A.q1`) — the unit of cost analytics.
- **Out:** the callable's value; side effects: ledger row, log events on
  queue waits and budget warnings (`budget.warn_usd`).
- **Ledger row:** `ts, purpose_tag, model, input_tokens, output_tokens,
  cost_usd, latency_ms, status∈{ok, retry_ok, retries_exhausted}` —
  append-only JSONL at `results/ledger.jsonl`. Pricing per MTok lives in
  `config/setup.json:pricing_per_mtok`; unknown models price as 0 but are
  still recorded (visible in audit, never silently lost).
- `LlmClient` **cannot be constructed without a gatekeeper**
  (`GatekeeperRequiredError`) — bypass is structurally impossible, not
  merely discouraged.

## 3. Constraints, alternatives, rationale

| Decision | Alternatives | Why chosen |
|---|---|---|
| Injected `clock`/`sleeper` | freezegun, real sleeps | tests control time deterministically; zero test latency |
| Sliding deque windows | token bucket, external limiter (e.g. `limits` lib) | exact §5.2 schema match, ~30 lines, no dependency |
| Budget check *before* call | post-hoc accounting only | a loop that has already overspent must not start one more call |
| JSONL ledger | CSV, SQLite | append-only crash-safe, greppable, schema-evolvable |
| Transport maps errors → `TransientApiError` | gatekeeper inspects provider exceptions | gatekeeper stays provider-agnostic (ports & adapters, ADR-7) |

Constraints: file ≤150 code lines; all limits/prices/budgets from config
(none in code); secrets only via env (`config.get_secret`).

## 4. Success criteria & test scenarios

All implemented in `tests/unit/test_gatekeeper.py`, `test_ledger.py`,
`test_llm_client.py` (FakeClock/FakeTransport, no real time or network):

- value passthrough; every call produces exactly one ledger row with the
  purpose tag and provider-reported tokens;
- within-limit calls never sleep; the (rpm+1)-th call waits ≈ window
  remainder; queue stats exposed;
- transient failure → backoff → success logs `retry_ok`; persistent
  failure raises `RetriesExhaustedError` and logs `retries_exhausted`;
  non-transient errors propagate immediately with no retry;
- spend ≥ `max_usd` blocks the *next* call with `BudgetExceededError`;
- `LlmClient(config, None, transport)` raises; tier→model resolution and
  `max_output_tokens` come from config.

**KPI:** 100% of LLM calls in the final report's ledger carry a purpose
tag; zero API calls outside the gatekeeper (code-review + grep gate).
