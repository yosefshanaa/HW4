"""mini_repo's own tiny suite — lets fix-loop tests run real pytest."""

from app.engine import parse, run, summarize


def test_parse_reads_name_value_lines():
    samples = parse("a=1.0\nb=3.0")
    assert [(s.name, s.value) for s in samples] == [("a", 1.0), ("b", 3.0)]


def test_summarize_means_and_clamps_peak():
    stats = summarize(parse("a=50\nb=150"))
    assert stats == {"mean": 100.0, "peak": 100.0}


def test_run_renders_full_report():
    out = run("My Title", "a=1.0")
    assert "# my-title" in out and "peak=1.0" in out and "id=my-title" in out
