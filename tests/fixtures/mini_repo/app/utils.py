"""Shared helpers — the planted HEALTHY hub (high fan-in, one concern)."""


def clamp(value, low, high):
    return max(low, min(high, value))


def mean(values):
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def slugify(text):
    return "-".join(text.lower().split())
