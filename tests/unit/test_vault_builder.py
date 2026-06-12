"""Tests for hw4.services.vault_builder — taxonomy, ownership, append-only."""

import yaml

from hw4.services.vault_builder import AUTO_MARK, TAXONOMY, VaultBuilder
from hw4.shared.config import Config

from .test_config import write_config_dir


def make_builder(tmp_path):
    setup = {
        "version": "1.00",
        "paths": {"vault": "vault", "results": "results"},
        "vault": {
            "project": "proj-x",
            "domains": ["python", "cli"],
            "top_hub_pages": 5,
            "wiki_page_max_lines": 40,
            "index_max_entries_per_section": 8,
        },
    }
    cfg = Config(write_config_dir(tmp_path / "cfg", setup=setup), environ={})
    return VaultBuilder(cfg, base_dir=tmp_path)


def parse_frontmatter(path):
    text = path.read_text()
    assert text.startswith("---\n")
    block = text.split("---\n")[1]
    return yaml.safe_load(block)


class TestSkeleton:
    def test_taxonomy_and_project_anatomy_created(self, tmp_path):
        builder = make_builder(tmp_path)
        builder.build_skeleton()
        for name in TAXONOMY:
            assert (tmp_path / "vault" / name).is_dir()
        assert builder.raw_dir.is_dir() and builder.wiki_dir.is_dir()
        assert builder.log_path.exists()

    def test_frontmatter_is_valid_yaml_with_routing_fields(self, tmp_path):
        builder = make_builder(tmp_path)
        builder.build_skeleton()
        meta = parse_frontmatter(tmp_path / "vault" / "00_Portfolio" / "Portfolio.md")
        assert meta == {"type": "portfolio", "status": "active", "project": "proj-x"}
        domain_meta = parse_frontmatter(tmp_path / "vault" / "10_Domains" / "python.md")
        assert domain_meta["type"] == "domain"

    def test_rerun_is_idempotent_and_never_clobbers_human_edits(self, tmp_path):
        builder = make_builder(tmp_path)
        builder.build_skeleton()
        note = tmp_path / "vault" / "10_Domains" / "python.md"
        note.write_text("HUMAN EDIT — must survive\n")
        second_run_created = builder.build_skeleton()
        assert note.read_text() == "HUMAN EDIT — must survive\n"
        assert note not in second_run_created


class TestIndex:
    def test_index_is_machine_owned_and_stable(self, tmp_path):
        builder = make_builder(tmp_path)
        builder.build_skeleton()
        sections = {"Communities": ["[[c0 — core]]", "[[c1 — io]]"], "Hubs": ["[[hub-a]]"]}
        builder.write_index(sections)
        first = builder.index_path.read_text()
        builder.write_index(sections)
        assert builder.index_path.read_text() == first  # regeneration is stable
        assert AUTO_MARK in first
        assert first.index("Communities") < first.index("Hubs")

    def test_index_fits_one_screen_for_typical_sections(self, tmp_path):
        builder = make_builder(tmp_path)
        builder.build_skeleton()
        builder.write_index({"Hubs": [f"[[h{i}]]" for i in range(5)]})
        assert len(builder.index_path.read_text().splitlines()) < 30


class TestLog:
    def test_log_is_append_only(self, tmp_path):
        builder = make_builder(tmp_path)
        builder.build_skeleton()
        builder.append_log("graph i00 ingested", "results/graphs/i00", "graph_runner")
        builder.append_log("wiki page core", "graph i00", "wiki_writer")
        lines = [ln for ln in builder.log_path.read_text().splitlines() if ln.startswith("- ")]
        assert len(lines) == 2
        assert "graph i00 ingested" in lines[0] and "wiki page core" in lines[1]


class TestRtlSafety:
    def test_hebrew_content_round_trips(self, tmp_path):
        """R11/T196: RTL content must survive write/read without mangling."""
        builder = make_builder(tmp_path)
        builder.build_skeleton()
        hebrew = "גרף הידע מציג צוואר בקבוק"
        (builder.wiki_dir / "rtl-note.md").write_text(f"# note\n{hebrew}\n", encoding="utf-8")
        builder.append_log(f"ingested {hebrew}", "manual", "test")
        assert hebrew in (builder.wiki_dir / "rtl-note.md").read_text(encoding="utf-8")
        assert hebrew in builder.log_path.read_text(encoding="utf-8")
