"""Graph contract — the one schema every consumer reads (PLAN §2.1, FR-2.3).

Whatever backend produced the raw graph, it is normalized into these
models at load time; validation failures are errors *here*, at the
boundary, never downstream surprises. Conservative defaults follow
Part-C: an edge with missing/unknown evidence degrades to AMBIGUOUS
(with a warning), because unmarked inference must never masquerade as
extraction. Unknown relation types are preserved verbatim and logged —
we don't silently drop another tool's semantics.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from hw4.constants import EdgeEvidence
from hw4.shared.logging_setup import get_logger, log_event
from hw4.shared.version import __version__, assert_config_compatible

NODE_TYPES = frozenset({"function", "class", "module", "doc", "rationale"})
KNOWN_RELATIONS = frozenset(
    {
        "calls",
        "imports",
        "implements",
        "mentions",
        "tested_by",
        "rationale_for",
        "semantically_similar_to",
    }
)


class GraphValidationError(ValueError):
    """The raw graph violates the contract (dangling edge, bad type...)."""


@dataclass(frozen=True)
class Node:
    """One entity in the knowledge graph."""

    id: str
    type: str
    label: str
    source_file: str = ""
    community: int = -1


@dataclass(frozen=True)
class Edge:
    """One relation, always carrying its evidence class (Part-C)."""

    src: str
    dst: str
    relation: str
    evidence: EdgeEvidence
    confidence: float


@dataclass
class Graph:
    """Validated in-memory graph + JSON (de)serialization."""

    version: str = __version__
    iteration: int = 0
    backend: str = ""
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict) -> Graph:
        assert_config_compatible(str(raw.get("version", "")), source="graph.json")
        logger = get_logger("graph")
        nodes: dict[str, Node] = {}
        for item in raw.get("nodes", []):
            node = _parse_node(item)
            nodes[node.id] = node
        edges = [_parse_edge(item, nodes, logger) for item in raw.get("edges", [])]
        return cls(
            version=str(raw["version"]),
            iteration=int(raw.get("iteration", 0)),
            backend=str(raw.get("backend", "")),
            nodes=nodes,
            edges=edges,
        )

    @classmethod
    def load(cls, path: Path | str) -> Graph:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "iteration": self.iteration,
            "backend": self.backend,
            "nodes": [asdict(node) for node in self.nodes.values()],
            "edges": [{**asdict(edge), "evidence": edge.evidence.value} for edge in self.edges],
        }

    def dump(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=1, sort_keys=True), encoding="utf-8")
        return path


def _parse_node(item: dict) -> Node:
    node_type = str(item.get("type", ""))
    if node_type not in NODE_TYPES:
        raise GraphValidationError(f"node {item.get('id')!r}: unknown type {node_type!r}")
    return Node(
        id=str(item["id"]),
        type=node_type,
        label=str(item.get("label", item["id"])),
        source_file=str(item.get("source_file", "")),
        community=int(item.get("community", -1)),
    )


def _parse_edge(item: dict, nodes: dict[str, Node], logger) -> Edge:
    src, dst = str(item.get("src")), str(item.get("dst"))
    for endpoint in (src, dst):
        if endpoint not in nodes:
            raise GraphValidationError(f"edge {src}->{dst}: dangling endpoint {endpoint!r}")
    relation = str(item.get("relation", ""))
    if relation not in KNOWN_RELATIONS:
        log_event(logger, "unknown relation preserved", relation=relation, src=src, dst=dst)
    raw_evidence = str(item.get("evidence", ""))
    try:
        evidence = EdgeEvidence(raw_evidence)
    except ValueError:
        log_event(logger, "evidence missing/unknown — degraded", edge=f"{src}->{dst}")
        evidence = EdgeEvidence.AMBIGUOUS
    return Edge(
        src=src,
        dst=dst,
        relation=relation,
        evidence=evidence,
        confidence=float(item.get("confidence", 0.5)),
    )
