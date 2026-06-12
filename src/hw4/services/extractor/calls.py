"""Call-edge extraction — who actually invokes whom (T137).

Resolution ladder, strictest first (Part-C evidence discipline):
1. name defined in the same module, or explicitly imported  -> EXTRACTED 1.0
2. `obj.attr()` where obj is a bound internal module        -> EXTRACTED 0.9
3. bare name defined in exactly ONE other module            -> INFERRED 0.6
4. anything else (zero or multiple candidates)              -> skipped —
   we never fabricate an edge we cannot defend.
"""

from __future__ import annotations

import ast

from hw4.constants import EdgeEvidence
from hw4.services.extractor.python_ast import PyModule
from hw4.services.graph_models import Edge


def unique_symbol_index(modules: list[PyModule]) -> dict[str, str]:
    """name -> node id, only for names defined in exactly one module."""
    seen: dict[str, list[str]] = {}
    for mod in modules:
        for name, node_id in mod.symbols.items():
            seen.setdefault(name, []).append(node_id)
    return {name: ids[0] for name, ids in seen.items() if len(ids) == 1}


def call_edges(
    mod: PyModule, by_name: dict[str, PyModule], unique_symbols: dict[str, str]
) -> list[Edge]:
    edges = []
    for owner_id, body in _owners(mod):
        for node in body:
            for call in (c for c in ast.walk(node) if isinstance(c, ast.Call)):
                resolved = _resolve(call.func, mod, by_name, unique_symbols)
                if resolved is None:
                    continue
                target, evidence, confidence = resolved
                if target != owner_id:
                    edges.append(
                        Edge(
                            src=owner_id,
                            dst=target,
                            relation="calls",
                            evidence=evidence,
                            confidence=confidence,
                        )
                    )
    return _dedupe(edges)


def _owners(mod: PyModule):
    """(caller node id, statements) — functions, methods, module level."""
    module_level = []
    for item in mod.tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield f"{mod.name}.{item.name}", item.body
        elif isinstance(item, ast.ClassDef):
            for sub in item.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield f"{mod.name}.{item.name}.{sub.name}", sub.body
        else:
            module_level.append(item)
    if module_level:
        yield mod.name, module_level


def _resolve(func, mod, by_name, unique_symbols):
    if isinstance(func, ast.Name):
        local = mod.symbols.get(func.id) or mod.bindings.get(func.id)
        if local:
            return local, EdgeEvidence.EXTRACTED, 1.0
        if func.id in unique_symbols:
            return unique_symbols[func.id], EdgeEvidence.INFERRED, 0.6
    elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        bound = mod.bindings.get(func.value.id, "")
        target_mod = by_name.get(bound)
        if target_mod:
            symbol = target_mod.symbols.get(func.attr)
            if symbol:
                return symbol, EdgeEvidence.EXTRACTED, 0.9
    return None


def _dedupe(edges: list[Edge]) -> list[Edge]:
    seen, kept = set(), []
    for edge in edges:
        key = (edge.src, edge.dst, edge.relation)
        if key not in seen:
            seen.add(key)
            kept.append(edge)
    return kept
