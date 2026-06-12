"""Pipeline entry point — the planted GOD NODE.

Imports every sibling module and mixes three concerns (parsing,
computation, presentation) that belong in separate components.
"""

from app.models import Sample
from app.reports import render
from app.utils import clamp, mean, slugify


def parse(raw):
    samples = []
    for line in raw.strip().splitlines():
        name, _, value = line.partition("=")
        samples.append(Sample(name.strip(), float(value)))
    return samples


def summarize(samples):
    values = [s.value for s in samples]
    return {"mean": mean(values), "peak": clamp(max(values), 0.0, 100.0)}


def run(title, raw):
    samples = [s.bounded() for s in parse(raw)]
    stats = summarize(samples)
    return f"{render(title, samples)}\npeak={stats['peak']}\nid={slugify(title)}"
