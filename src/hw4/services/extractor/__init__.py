"""AST fallback extraction backend (ADR-4) — emits the PLAN §2.1 contract.

Split by evolution speed: python_ast.py reads code (EXTRACTED world),
docs.py reads prose (INFERRED/AMBIGUOUS world), backend.py assembles.
"""

from hw4.services.extractor.backend import BACKEND_ID, extract

__all__ = ["BACKEND_ID", "extract"]
