"""Record types for measurements."""

from dataclasses import dataclass

from app.utils import clamp


@dataclass
class Sample:
    name: str
    value: float

    def bounded(self, low=0.0, high=100.0):
        return Sample(self.name, clamp(self.value, low, high))
