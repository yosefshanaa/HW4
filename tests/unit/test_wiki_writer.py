"""Tests for hw4.services.wiki_writer — mocked LLM, programmatic facts."""

import re

from hw4.services.graph_metrics import compute
from hw4.services.vault_builder import VaultBuilder
from hw4.services.wiki_writer import WikiWriter, select_entities
from hw4.shared.config import Config
from hw4.shared.llm_client import LlmClient

from .test_config import write_config_dir
from .test_gatekeeper import make_gatekeeper
from .test_graph_metrics import planted_graph
from .test_llm_client import FakeTransport, response

PROSE = "SUMMARY: A central node, evidence suggests a bottleneck.\nOPEN QUESTIONS:\n- why?\n"


def make_setup(tmp_path):
    return {
        "version": "1.00",
        "paths": {"vault": "vault", "results": "results"},
        "models": {"cheap": "model-cheap", "strong": "model-strong"},
        "llm": {"max_output_tokens": 64, "api_key_env": "K"},
        "metrics": {"relations": ["imports", "calls"], "top_k_bottlenecks": 3},
        "vault": {
            "project": "proj-x", "domains": ["python"], "top_hub_pages": 2,
            "wiki_page_max_lines": 40, "index_max_entries_per_section": 8,
            "min_community_size": 3,
        },
    }


def make_writer(tmp_path, script):
    cfg = Config(write_config_dir(tmp_path / "cfg", setup=make_setup(tmp_path)), environ={})
    gate, ledger, _ = make_gatekeeper(tmp_path)
    llm = LlmClient(cfg, gate, FakeTransport(script))
    vault = VaultBuilder(cfg, base_dir=tmp_path)
    vault.build_skeleton()
    return WikiWriter(cfg, llm, vault), vault, cfg, ledger


def write_all(tmp_path, prose=PROSE, n_pages=10):
    graph = planted_graph()
    writer, vault, cfg, ledger = make_writer(
        tmp_path, [response(text=prose) for _ in range(n_pages)]
    )
    metrics = compute(graph, cfg)
    return writer.write_pages(graph, metrics, cfg), vault, ledger


class TestSelection:
    def test_hubs_and_big_communities_selected(self, tmp_path):
        graph = planted_graph()
        cfg = Config(write_config_dir(tmp_path / "cfg", setup=make_setup(tmp_path)), environ={})
        specs = select_entities(graph, compute(graph, cfg), cfg)
        kinds = {s.kind for s in specs}
        assert kinds == {"hub", "community"}
        hub_ids = [s.page_id for s in specs if s.kind == "hub"]
        assert "hub" in hub_ids  # the planted bottleneck gets a page


class TestRendering:
    def test_pages_written_with_all_sections(self, tmp_path):
        paths, _, _ = write_all(tmp_path)
        text = next(p for p in paths if p.stem == "hub").read_text()
        for section in ("## Summary", "## Evidence", "## Links", "## Open questions"):
            assert section in text
        assert "evidence suggests a bottleneck" in text

    def test_evidence_rows_are_programmatic_not_llm(self, tmp_path):
        paths, _, _ = write_all(tmp_path, prose="SUMMARY: x\nOPEN QUESTIONS:\n- q\n")
        text = next(p for p in paths if p.stem == "hub").read_text()
        assert re.search(r"—calls→ .* \(EXTRACTED, 1\.00\)", text)

    def test_wikilink_integrity_no_dangling_links(self, tmp_path):
        paths, _, _ = write_all(tmp_path)
        produced = {p.stem for p in paths} | {"index"}
        for path in paths:
            for link in re.findall(r"\[\[([^\]]+)\]\]", path.read_text()):
                assert link in produced, f"dangling link {link} in {path.name}"

    def test_length_cap_enforced(self, tmp_path):
        long_prose = "SUMMARY: " + "word " * 30 + "\nOPEN QUESTIONS:\n" + "- q\n" * 30
        paths, _, _ = write_all(tmp_path, prose=long_prose)
        for path in paths:
            assert len(path.read_text().splitlines()) <= 41

    def test_every_generation_ledgered_with_purpose_tag(self, tmp_path):
        paths, _, ledger = write_all(tmp_path)
        tags = [e.purpose_tag for e in ledger.entries()]
        assert len(tags) == len(paths)
        assert all(tag.startswith("wiki.gen.") for tag in tags)

    def test_ingestion_logged_per_page(self, tmp_path):
        paths, vault, _ = write_all(tmp_path)
        log = vault.log_path.read_text()
        assert sum("wiki page" in ln for ln in log.splitlines()) == len(paths)
