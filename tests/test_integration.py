"""MAYDAY RECON - Integration Tests"""

import pytest
import yaml
import tempfile
import os
from pathlib import Path

from mayday.agents.reconbot import ReconBot, AttackDefinition
from mayday.reconciliation_engine import ReconciliationEngine


class TestAttackDSL:
    """Test DSL loading and parsing"""

    def test_load_dsl_file(self):
        """Test loading DSL file from disk"""
        engine = ReconciliationEngine()
        dsl_path = "mayday/attack.dsl.yml"
        assert os.path.exists(dsl_path), f"DSL file not found at {dsl_path}"

        result = engine.load_dsl(dsl_path)
        assert result["valid"], "DSL loading should succeed"
        assert len(engine.reconbot.attacks) > 0, "Should have loaded at least one attack"


class TestReconBot:
    """Test ReconBot agent functionality"""

    def test_reconbot_initialization(self):
        """Test ReconBot can be initialized with DSL"""
        bot = ReconBot("mayday/attack.dsl.yml")
        assert bot is not None
        assert len(bot.attacks) > 0

    def test_attack_definition_structure(self):
        """Test attack definitions have required structure"""
        bot = ReconBot("mayday/attack.dsl.yml")

        for attack_name, attack in bot.attacks.items():
            assert attack_name, "Attack should have a name"
            assert attack.description, f"{attack_name} should have a description"
            assert attack.type, f"{attack_name} should have a type"
            assert attack.severity, f"{attack_name} should have a severity"
            assert attack.stage, f"{attack_name} should have a stage"


class TestCFOSimulator:
    """Test CFO Simulator functionality"""

    def test_cfo_simulation(self):
        """Test CFO simulator can generate test data"""
        from simulator.cfo_simulator import CFOSimulator

        simulator = CFOSimulator(bank_name="Test Bank")

        # Generate transactions
        transactions = simulator.generate_transactions(
            transaction_count=10,
            account_type="savings",
            date_range_days=30
        )

        assert len(transactions) > 0, "Should generate at least one transaction"
        assert transactions[0].account_id, "Transaction should have account ID"


class TestReconciliationEngine:
    """Test Reconciliation Engine orchestration"""

    def test_engine_initialization(self):
        """Test engine can be initialized"""
        engine = ReconciliationEngine()
        assert engine.reconbot is not None
        assert engine.simulator is not None

    def test_engine_initialization_from_dsl(self):
        """Test engine loads DSL on initialization"""
        engine = ReconciliationEngine(dsl_path="mayday/attack.dsl.yml")
        engine.initialize_from_dsl()
        assert len(engine.reconbot.attacks) > 0

    def test_load_dsl_with_yaml_error(self):
        """Test engine handles invalid YAML gracefully"""
        invalid_dsl = "invalid: yaml: content: [unbalanced"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(invalid_dsl)
            temp_path = f.name

        try:
            engine = ReconciliationEngine()
            result = engine.load_dsl(temp_path)
            assert not result["valid"], "Should fail on invalid YAML"
        finally:
            os.unlink(temp_path)

    def test_generate_test_suite(self):
        """Test engine can generate a test suite"""
        engine = ReconciliationEngine()
        engine.initialize_from_dsl()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name

        try:
            test_suite = engine.generate_test_suite(temp_path)
            assert "attacks" in test_suite
            assert len(test_suite["attacks"]) > 0
            assert os.path.exists(temp_path), "Test suite file should be created"
        finally:
            os.unlink(temp_path)


class TestAttackScenarios:
    """Test specific attack scenarios"""

    def test_transaction_fraud_attack(self):
        """Test transaction fraud attack injection"""
        bot = ReconBot("mayday/attack.dsl.yml")

        if "transaction_fraud" in bot.attacks:
            attack_instance = bot.inject_attack("transaction_fraud")
            assert attack_instance is not None
            assert attack_instance.status in ["pending", "injected", "detected"]

    def test_gl_mismatch_attack(self):
        """Test GL mismatch attack injection"""
        bot = ReconBot("mayday/attack.dsl.yml")

        if "GL_mismatch" in bot.attacks:
            attack_instance = bot.inject_attack("GL_mismatch")
            assert attack_instance is not None
            assert attack_instance.status in ["pending", "injected", "detected"]


class TestReconciliationWorkflow:
    """Test complete reconciliation workflow"""

    def test_standard_reconciliation_test(self):
        """Test complete reconciliation test execution"""
        engine = ReconciliationEngine()
        engine.initialize_from_dsl()

        # Run a test with minimal filters
        test_report = engine.run_reconciliation_test(
            test_name="test-complete-workflow",
            attack_filters=None,
            severity_threshold="low"
        )

        assert test_report["test_name"] == "test-complete-workflow"
        assert "stages" in test_report
        assert len(test_report["stages"]) > 0

    def test_stage_execution_order(self):
        """Test stages execute in correct order"""
        engine = ReconciliationEngine()
        engine.initialize_from_dsl()

        test_report = engine.run_reconciliation_test(
            test_name="test-stage-order"
        )

        stages = [stage["stage"] for stage in test_report["stages"]]
        expected_stages = ["load", "transform", "validate", "match", "report"]

        assert stages == expected_stages, f"Stages should be in order: {stages} != {expected_stages}"

    def test_attack_detection_logic(self):
        """Test that attacks can be detected"""
        # This test would need a more sophisticated attack configuration
        # to properly verify detection logic
        bot = ReconBot("mayday/attack.dsl.yml")

        if len(bot.attacks) > 0:
            # Inject first attack
            first_attack = list(bot.attacks.keys())[0]
            attack_instance = bot.inject_attack(first_attack)

            # Verify injection was successful
            assert attack_instance is not None
            assert attack_instance.attack_id is not None


def run_integration_tests():
    """Run integration tests with pytest"""
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    run_integration_tests()
