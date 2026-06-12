"""Execute notebooks/analysis.ipynb top-to-bottom (T383 verification).

Run: uv run --with nbformat --with nbclient --with ipykernel \
         --with matplotlib python scripts/execute_notebook.py
Writes the executed notebook in place (outputs embedded) and exits
nonzero on any cell error — restart-kernel/run-all, scripted.
"""

from __future__ import annotations

import sys
import time

import nbformat
from nbclient import NotebookClient

PATH = "notebooks/analysis.ipynb"


def main() -> int:
    nb = nbformat.read(PATH, as_version=4)
    started = time.monotonic()
    client = NotebookClient(nb, timeout=300, kernel_name="python3")
    client.execute()
    nbformat.write(nb, PATH)
    print(f"executed {len(nb.cells)} cells in {time.monotonic() - started:.1f}s -> {PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
