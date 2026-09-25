"""
Unit tests for AI evaluation metrics calculation.
"""

from backend.src.ai.evaluation.metrics import calculate_metrics


def test_perfect_detection_metrics():
    metrics = calculate_metrics(tp=10, fp=0, fn=0, critical_expected=4, critical_detected=4)
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["critical_error_recall"] == 1.0


def test_zero_division_resilience():
    """Empty cases must not crash with ZeroDivisionError."""
    metrics = calculate_metrics(tp=0, fp=0, fn=0, critical_expected=0, critical_detected=0)
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["critical_error_recall"] == 1.0


def test_partial_detection_metrics():
    metrics = calculate_metrics(tp=6, fp=2, fn=4, critical_expected=5, critical_detected=4)
    # Precision = 6 / 8 = 0.75
    assert metrics["precision"] == 0.75
    # Recall = 6 / 10 = 0.60
    assert metrics["recall"] == 0.60
    # F1 = 2 * (0.75 * 0.60) / (0.75 + 0.60) = 0.90 / 1.35 = 0.6667
    assert metrics["f1_score"] == 0.6667
    # Critical Recall = 4 / 5 = 0.80
    assert metrics["critical_error_recall"] == 0.80
