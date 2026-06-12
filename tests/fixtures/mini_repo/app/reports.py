"""Plain-text report rendering."""

from app.utils import mean, slugify


def render(title, samples):
    lines = [f"# {slugify(title)}", f"mean={mean(s.value for s in samples):.2f}"]
    lines += [f"- {s.name}: {s.value}" for s in samples]
    return "\n".join(lines)
