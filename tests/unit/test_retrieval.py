"""Tests for hw4.services.retrieval — matching, caps, edge placement."""

import pytest

from hw4.services.retrieval import NoRetrievalMatchError, Retriever
from hw4.services.vault_builder import VaultBuilder
from hw4.shared.config import Config

from .test_config import write_config_dir
from .test_graph_metrics import planted_graph


def make_retriever(tmp_path, token_cap=12000, max_nodes=40):
    setup = {
        "version": "1.00",
        "paths": {"vault": "vault", "results": "results"},
        "retrieval": {
            "k_pages": 2, "ego_radius": 2, "max_nodes": max_nodes,
            "max_seeds": 3, "context_token_cap": token_cap,
        },
        "vault": {
            "project": "proj-x", "domains": ["python"], "top_hub_pages": 5,
            "wiki_page_max_lines": 40, "index_max_entries_per_section": 8,
            "min_community_size": 3,
        },
    }
    cfg = Config(write_config_dir(tmp_path / "cfg", setup=setup), environ={})
    vault = VaultBuilder(cfg, base_dir=tmp_path)
    vault.build_skeleton()
    vault.write_index({"Hubs": ["[[hub]]"]})
    (vault.wiki_dir / "hub.md").write_text("# hub — bottleneck\nthe hub joins a and b\n")
    (vault.wiki_dir / "community-0.md").write_text("# community 0\nnodes a1 a2 a3\n")
    return Retriever(cfg, vault), vault


class TestMatching:
    def test_question_terms_match_node_and_pages(self, tmp_path):
        retriever, _ = make_retriever(tmp_path)
        bundle = retriever.retrieve("why is hub a bottleneck?", planted_graph())
        assert "hub" in bundle.matched_nodes
        assert any(pid == "hub" for pid, _ in bundle.wiki_pages)

    def test_no_match_raises_instead_of_guessing(self, tmp_path):
        retriever, _ = make_retriever(tmp_path)
        with pytest.raises(NoRetrievalMatchError):
            retriever.retrieve("what about quantum blockchain?", planted_graph())


class TestBundle:
    def test_assembly_edge_placement(self, tmp_path):
        retriever, _ = make_retriever(tmp_path)
        bundle = retriever.retrieve("hub bottleneck?", planted_graph())
        text = bundle.assemble("INSTRUCTIONS-FIRST")
        assert text.startswith("INSTRUCTIONS-FIRST")
        assert text.rstrip().endswith("QUESTION: hub bottleneck?")
        assert text.index("focused subgraph") < text.index("QUESTION:")

    def test_subgraph_respects_node_cap(self, tmp_path):
        retriever, _ = make_retriever(tmp_path, max_nodes=3)
        bundle = retriever.retrieve("hub bottleneck?", planted_graph())
        node_lines = [ln for ln in bundle.subgraph_text.splitlines() if ln.startswith("node ")]
        assert len(node_lines) <= 3 * 3  # <= max_nodes per seed, 3 seeds max

    def test_source_files_surfaced_for_citations(self, tmp_path):
        retriever, _ = make_retriever(tmp_path)
        bundle = retriever.retrieve("hub bottleneck?", planted_graph())
        assert isinstance(bundle.source_files, list)


class TestTokenGuard:
    def test_estimate_reported(self, tmp_path):
        retriever, _ = make_retriever(tmp_path)
        bundle = retriever.retrieve("hub bottleneck?", planted_graph())
        assert bundle.token_estimate > 0
        assert not bundle.truncated

    def test_tiny_cap_drops_pages_then_truncates_subgraph(self, tmp_path):
        retriever, _ = make_retriever(tmp_path, token_cap=40)
        bundle = retriever.retrieve("hub bottleneck?", planted_graph())
        assert bundle.truncated
        assert len(bundle.wiki_pages) < 2
