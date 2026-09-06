"""
MAYDAY RECON benchmark CLI (PRD section 10).

Usage:
    python benchmark.py --suite holdout
    python benchmark.py --suite training --agent-version v0.2
    python benchmark.py --suite all --agent-version v0.1
"""
import argparse
import json
import sys

from benchmark.run_benchmark import BenchmarkRunner
from simulator.db.database import DB_FILE


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="MAYDAY RECON benchmark runner")
    parser.add_argument(
        "--suite",
        choices=["training", "holdout", "all"],
        default="holdout",
        help="Attack suite to run (default: holdout)",
    )
    parser.add_argument(
        "--agent-version",
        choices=["v0.1", "v0.2"],
        default="v0.2",
        help="Agent version under test (default: v0.2)",
    )
    parser.add_argument(
        "--report",
        default="benchmark_report.json",
        help="Path to write the JSON report (default: benchmark_report.json)",
    )
    return parser.parse_args(argv)


def print_comparison_table(before, after):
    rows = [
        ("Scenarios (passed/total)",
         f"{before['passed_scenarios']}/{before['total_scenarios']}",
         f"{after['passed_scenarios']}/{after['total_scenarios']}"),
        ("Accuracy %", f"{before['accuracy_pct']}", f"{after['accuracy_pct']}"),
        ("Avg FAR", f"{before['average_far_score']}", f"{after['average_far_score']}"),
        ("Unsafe mutations", f"{before['total_unsafe_mutations']}", f"{after['total_unsafe_mutations']}"),
        ("Production ready", f"{before['production_ready']}", f"{after['production_ready']}"),
    ]
    print()
    print("=" * 72)
    print(" MAYDAY RECON — BENCHMARK BEFORE/AFTER")
    print("=" * 72)
    print(f" Suite: {before['suite_type']}")
    print(f" {'Metric':<28}{'BEFORE (v0.1)':<20}{'AFTER (v0.2)':<20}")
    print("-" * 72)
    for metric, b, a in rows:
        print(f" {metric:<28}{b:<20}{a:<20}")
    print("-" * 72)
    for key in ("correctness", "safety", "recovery", "policy_compliance",
                "auditability", "tool_calls_per_task", "latency_ms_per_task",
                "cost_usd_per_task"):
        bm = before["metrics"].get(key)
        am = after["metrics"].get(key)
        print(f" {key:<28}{bm:<20}{am:<20}")
    print("=" * 72)


def main(argv=None):
    args = parse_args(argv)
    runner = BenchmarkRunner(DB_FILE)

    print(f"[Benchmark] suite={args.suite} agent_version={args.agent_version}")
    under_test = runner.run_suite(agent_version=args.agent_version, suite_type=args.suite)

    # BEFORE/AFTER comparison across both agent versions.
    if args.agent_version == "v0.1":
        before, after = under_test, runner.run_suite(agent_version="v0.2", suite_type=args.suite)
    else:
        before, after = runner.run_suite(agent_version="v0.1", suite_type=args.suite), under_test

    print_comparison_table(before, after)

    report = {
        "suite": args.suite,
        "agent_version": args.agent_version,
        "under_test": under_test,
        "before_v01": before,
        "after_v02": after,
    }
    with open(args.report, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[Benchmark] report saved to {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
