"""
Command-line runner for AI QC Evaluation Benchmark & Quality Gate.
Usage:
    python -m backend.src.evaluation_cli [--output-json benchmark_results.json]
"""

import argparse
import os
import sys
import tempfile

from .ai.evaluation.gold_dataset import GoldDatasetManager
from .ai.evaluation.runner import EvaluationRunner


def main():
    parser = argparse.ArgumentParser(description="Wiring Diagram QC Assistant — AI Evaluation Benchmark")
    parser.add_argument("--output-json", help="Path to write benchmark report JSON")
    parser.add_argument("--data-dir", help="Directory to store/load gold dataset PDFs")
    args = parser.parse_args()

    print("\n=======================================================")
    print("  Wiring Diagram QC — AI Evaluation Framework")
    print("=======================================================")

    with tempfile.TemporaryDirectory() as tmpdir:
        dataset_dir = args.data_dir or tmpdir
        print(f"Setting up Gold Dataset in: {dataset_dir}")
        test_cases = GoldDatasetManager.setup_dataset(dataset_dir)
        print(f"Loaded {len(test_cases)} benchmark test cases.")

        print("Executing benchmark runs across all cases...\n")
        runner = EvaluationRunner()
        report = runner.run_benchmark(test_cases)

        # Print Case-by-Case Breakdown
        print(f"{'Case ID':<8} | {'Case Name':<35} | {'Expected':<8} | {'Detected':<8} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'Status'}")
        print("-" * 95)
        for c in report.case_results:
            status_symbol = "✓ PASS" if c.passed_overall_status_match else "✗ FAIL"
            print(f"{c.case_id:<8} | {c.case_name[:35]:<35} | {c.expected_findings_count:<8} | {c.predicted_findings_count:<8} | {c.true_positives:<4} | {c.false_positives:<4} | {c.false_negatives:<4} | {status_symbol}")

        print("\n" + "=" * 55)
        print("  AGGREGATE BENCHMARK METRICS")
        print("=" * 55)
        print(f"Total Test Cases:            {report.total_cases}")
        print(f"Passed Overall Status:       {report.cases_passed_status} / {report.total_cases}")
        print(f"Total Expected Findings:     {report.total_expected_findings}")
        print(f"Total Predicted Findings:    {report.total_predicted_findings}")
        print(f"True Positives (TP):         {report.total_true_positives}")
        print(f"False Positives (FP):        {report.total_false_positives}")
        print(f"False Negatives (FN):        {report.total_false_negatives}")
        print(f"Precision:                   {report.precision * 100:.1f}%")
        print(f"Recall:                      {report.recall * 100:.1f}%")
        print(f"F1 Score:                    {report.f1_score * 100:.1f}%")
        print(f"CRITICAL ERROR RECALL:       {report.critical_error_recall * 100:.1f}% (Gate: >= 98.0%)")
        print("=" * 55)

        gate_status = "PASSED ✓" if report.passed_quality_gate else "FAILED ✗"
        print(f"QUALITY GATE STATUS: {gate_status}\n")

        if args.output_json:
            with open(args.output_json, "w") as f:
                f.write(report.model_dump_json(indent=2))
            print(f"Benchmark report saved to: {args.output_json}")

        if not report.passed_quality_gate:
            print("Error: AI Evaluation Quality Gate was not met!", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
