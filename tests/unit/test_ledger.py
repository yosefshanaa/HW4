"""Tests for hw4.shared.ledger — pricing, append, aggregation."""

from hw4.shared.config import Config
from hw4.shared.ledger import Ledger

from .test_config import write_config_dir

PRICING = {
    "model-x": {"input": 2.0, "output": 10.0},
}


def make_ledger(tmp_path):
    setup = {
        "version": "1.00",
        "paths": {"results": "results"},
        "pricing_per_mtok": PRICING,
    }
    cfg = Config(write_config_dir(tmp_path / "cfg", setup=setup), environ={})
    return Ledger(cfg, tmp_path / "results" / "ledger.jsonl")


class TestPricing:
    def test_cost_from_config_price_table(self, tmp_path):
        ledger = make_ledger(tmp_path)
        # 1M input @ $2 + 0.5M output @ $10 = 2 + 5 = 7
        assert ledger.cost_of("model-x", 1_000_000, 500_000) == 7.0

    def test_unknown_model_priced_zero_not_crash(self, tmp_path):
        assert make_ledger(tmp_path).cost_of("mystery", 1000, 1000) == 0.0


class TestRecord:
    def test_appends_jsonl_row_with_computed_cost(self, tmp_path):
        ledger = make_ledger(tmp_path)
        entry = ledger.record(
            purpose_tag="experiment.A.q1",
            model="model-x",
            input_tokens=10_000,
            output_tokens=1_000,
            latency_ms=120,
        )
        assert entry.cost_usd == round((10_000 * 2 + 1_000 * 10) / 1_000_000, 6)
        assert len(ledger.entries()) == 1

    def test_creates_parent_directory(self, tmp_path):
        ledger = make_ledger(tmp_path)
        ledger.record(
            purpose_tag="t", model="model-x", input_tokens=1, output_tokens=1, latency_ms=1
        )
        assert (tmp_path / "results" / "ledger.jsonl").is_file()

    def test_round_trip_preserves_fields(self, tmp_path):
        ledger = make_ledger(tmp_path)
        ledger.record(
            purpose_tag="wiki.gen",
            model="model-x",
            input_tokens=5,
            output_tokens=7,
            latency_ms=33,
            status="retry_ok",
        )
        entry = ledger.entries()[0]
        assert entry.purpose_tag == "wiki.gen"
        assert entry.status == "retry_ok"


class TestAggregation:
    def test_totals_filter_by_purpose_prefix(self, tmp_path):
        ledger = make_ledger(tmp_path)
        for tag, tokens in [("experiment.A.q1", 100), ("experiment.B.q1", 40), ("wiki.gen", 9)]:
            ledger.record(
                purpose_tag=tag,
                model="model-x",
                input_tokens=tokens,
                output_tokens=0,
                latency_ms=1,
            )
        assert ledger.totals("experiment.")["input_tokens"] == 140
        assert ledger.totals("experiment.A")["calls"] == 1
        assert ledger.totals()["calls"] == 3

    def test_total_cost_sums_everything(self, tmp_path):
        ledger = make_ledger(tmp_path)
        ledger.record(
            purpose_tag="a", model="model-x", input_tokens=1_000_000, output_tokens=0, latency_ms=1
        )
        ledger.record(
            purpose_tag="b", model="model-x", input_tokens=0, output_tokens=100_000, latency_ms=1
        )
        assert ledger.total_cost() == 3.0  # $2 + $1

    def test_empty_ledger_reads_as_empty(self, tmp_path):
        assert make_ledger(tmp_path).entries() == []
