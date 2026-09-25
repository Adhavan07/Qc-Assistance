"""
AI Evaluation Framework package.
"""
from .metrics import (
    GroundTruthFinding,
    EvaluationTestCase,
    CaseEvaluationResult,
    BenchmarkReport,
    calculate_metrics,
)
from .gold_dataset import GoldDatasetManager
from .runner import EvaluationRunner

__all__ = [
    "GroundTruthFinding",
    "EvaluationTestCase",
    "CaseEvaluationResult",
    "BenchmarkReport",
    "calculate_metrics",
    "GoldDatasetManager",
    "EvaluationRunner",
]
