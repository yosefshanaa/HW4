"""Detector evaluation — confusion matrix against a labeled answer key."""

from hw4.services.evaluation.confusion import (
    Candidate,
    ConfusionMatrix,
    Outcome,
    evaluate,
    load_answer_key,
)

__all__ = ["Candidate", "ConfusionMatrix", "Outcome", "evaluate", "load_answer_key"]
