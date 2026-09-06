"""
Pytest integration for MAYDAY Evaluator Self-Test suite.
Verifies grader accuracy on edge cases, safety violations, FAR metric math, and exposure calculation.
"""
import pytest
from mayday.evaluator.evaluator_self_test import EvaluatorSelfTest, run_self_test


def test_evaluator_self_test_suite():
    """Run full EvaluatorSelfTest suite and assert all edge cases pass."""
    summary = run_self_test()
    assert summary["success"] is True, f"Evaluator self-test failed: {summary['failed']} failed tests out of {summary['total_tests']}"
    assert summary["passed"] == summary["total_tests"]
    assert summary["failed"] == 0


def test_evaluator_individual_cases():
    """Verify individual self-test methods directly."""
    self_test = EvaluatorSelfTest()

    self_test.test_flawless_execution()
    self_test.test_unsafe_mutation_duplicate_reconciliation()
    self_test.test_unsafe_mutation_forbidden_reconciliation()
    self_test.test_missing_mandatory_action_exception()
    self_test.test_safety_violation_detect_ambiguity()
    self_test.test_disallowed_agent_decision()
    self_test.test_recovery_failure_verify_postcondition()
    self_test.test_empty_and_null_inputs()
    self_test.test_malformed_state_after()
    self_test.test_efficiency_score_boundary()
    self_test.test_financial_exposure_custom_amount()
    self_test.test_far_score_exact_calculation()
    self_test.test_production_readiness_threshold()
