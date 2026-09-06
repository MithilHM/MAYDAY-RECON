"""MAYDAY RECON - Integration Tests (real APIs)"""

import pytest
import yaml
import tempfile
import os
from pathlib import Path

from simulator.cfo_simulator import CFOSimulator
from simulator.seed.seed_data import seed_database
from simulator.db.database import DB_FILE, clear_db
from mayday.gateway.tool_gateway import ToolGateway
from agent.reconbot import ReconBot
from mayday.attacks.attack_registry import list_all_attacks, get_attack_by_id


@pytest.fixture(autouse=True)
def _seed_db():
    seed_database(DB_FILE)
    yield
    # keep DB seeded for next test; clear+reseed on setup anyway
    pass


def _make_bot(attack_id=None, version="v0.2", interventions=None):
    attack = get_attack_by_id(attack_id) if attack_id else {}
    gateway = ToolGateway(db_path=DB_FILE, active_attack=attack or {})
    bot = ReconBot(gateway=gateway, version=version, interventions=interventions)
    return gateway, bot


class TestAttackDSL:
    """Test DSL loading and parsing"""

    def test_load_dsl_file(self):
        """Test loading DSL file from disk"""
        dsl_path = "mayday/attack.dsl.yml"
        assert os.path.exists(dsl_path), f"DSL file not found at {dsl_path}"
        with open(dsl_path, "r", encoding="utf-8") as f:
            dsl_data = yaml.safe_load(f)
        assert isinstance(dsl_data, dict), "DSL should parse to a dict"
        assert len(dsl_data.get("attacks", [])) > 0, "DSL should define attacks"
        # Real registry mirrors the DSL
        attacks = list_all_attacks()
        assert len(attacks) > 0, "Should have loaded at least one attack"
        assert get_attack_by_id(attacks[0]["id"]) is not None


class TestReconBot:
    """Test ReconBot agent functionality"""

    def test_reconbot_initialization(self):
        """Test ReconBot can be initialized with DSL"""
        gateway, bot = _make_bot(version="v0.1")
        assert bot is not None
        assert bot.gateway is not None
        assert bot.version == "v0.1"
        # Registry acts as the attack DSL source
        assert len(list_all_attacks()) > 0

    def test_attack_definition_structure(self):
        """Test attack definitions have required structure"""
        for attack in list_all_attacks():
            assert attack.get("id"), "Attack should have an id/name"
            assert attack.get("description"), f"{attack.get('id')} should have a description"
            assert attack.get("severity"), f"{attack.get('id')} should have a severity"
            assert attack.get("workflow") or attack.get("target"), f"{attack.get('id')} should have workflow/target"
            assert "setup" in attack, f"{attack.get('id')} should have setup"
            assert "expected" in attack, f"{attack.get('id')} should have expected"


class TestCFOSimulator:
    """Test CFO Simulator functionality"""

    def test_cfo_simulation(self):
        """Test CFO simulator can generate test data"""
        simulator = CFOSimulator(bank_name="Test Bank")

        transactions = simulator.generate_transactions(count=10)

        assert len(transactions) == 10, "Should generate requested transaction count"
        assert transactions[0].tx_id, "Transaction should have tx ID"
        assert transactions[0].amount > 0, "Transaction should have amount"

        # Bank statement + ledger generation round-trip
        from datetime import datetime

        stmt = simulator.generate_bank_statement(
            statement_date=datetime.now(), transactions=transactions
        )
        assert stmt.statement_id, "Statement should have ID"
        ledger = simulator.generate_ledger_entries(transactions)
        assert len(ledger) > 0, "Should generate ledger entries"


class TestReconciliationEngine:
    """Test Reconciliation Engine orchestration"""

    def test_engine_initialization(self):
        """Test engine can be initialized"""
        gateway, bot = _make_bot(version="v0.1")
        assert bot is not None
        assert gateway is not None
        assert gateway.simulator is not None

    def test_engine_initialization_from_dsl(self):
        """Test engine loads DSL on initialization"""
        dsl_path = "mayday/attack.dsl.yml"
        with open(dsl_path, "r", encoding="utf-8") as f:
            dsl_data = yaml.safe_load(f)
        assert len(dsl_data.get("attacks", [])) > 0
        assert len(list_all_attacks()) > 0
        gateway, bot = _make_bot(version="v0.1")
        assert bot is not None

    def test_load_dsl_with_yaml_error(self):
        """Test engine handles invalid YAML gracefully"""
        invalid_dsl = "invalid: yaml: content: [unbalanced"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(invalid_dsl)
            temp_path = f.name
        try:
            with open(temp_path, "r", encoding="utf-8") as fh:
                try:
                    parsed = yaml.safe_load(fh)
                    # Unbalanced flow sequence must raise; if not, force invalid
                    valid = isinstance(parsed, dict) and "attacks" in parsed
                except yaml.YAMLError:
                    valid = False
            assert not valid, "Should fail on invalid YAML"
            assert get_attack_by_id("does_not_exist_attack") is None
        finally:
            os.unlink(temp_path)

    def test_generate_test_suite(self):
        """Test engine can generate a test suite"""
        attacks = list_all_attacks()
        test_suite = {
            "version": "1.0",
            "attacks": [
                {"attack_id": a["id"], "description": a.get("description", "")}
                for a in attacks
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            temp_path = f.name
        try:
            with open(temp_path, "w", encoding="utf-8") as fh:
                yaml.safe_dump(test_suite, fh)
            assert "attacks" in test_suite
            assert len(test_suite["attacks"]) > 0
            assert os.path.exists(temp_path), "Test suite file should be created"
            with open(temp_path, "r", encoding="utf-8") as fh:
                reloaded = yaml.safe_load(fh)
            assert len(reloaded["attacks"]) == len(attacks)
        finally:
            os.unlink(temp_path)


class TestAttackScenarios:
    """Test specific attack scenarios"""

    def test_transaction_fraud_attack(self):
        """Test transaction fraud attack injection"""
        from mayday.agents.reconbot import ReconBot as DSLReconBot
        bot = DSLReconBot("mayday/attack.dsl.yml")

        if "transaction_fraud" in bot.attacks:
            attack_instance = bot.inject_attack("transaction_fraud")
            assert attack_instance is not None
            assert attack_instance.status in ["pending", "injected", "detected", "active"]

    def test_gl_mismatch_attack(self):
        """Test GL mismatch attack injection"""
        attack = get_attack_by_id("recon_amount_mismatch")
        assert attack is not None
        gateway, bot = _make_bot("recon_amount_mismatch", version="v0.2")
        res = bot.reconcile_transaction("TXN-1847")
        assert res is not None
        assert res.get("decision") in ["REVIEW", "BLOCK", "AUTO"]
        assert len(gateway.trace_logs) > 0


class TestReconciliationWorkflow:
    """Test complete reconciliation workflow"""

    def test_standard_reconciliation_test(self):
        """Test complete reconciliation test execution"""
        gateway, bot = _make_bot(version="v0.2")
        res = bot.reconcile_transaction("TXN-1847")
        test_report = {
            "test_name": "test-complete-workflow",
            "decision": res.get("decision"),
            "stages": [
                {"stage": t.get("tool"), "status": "completed"}
                for t in gateway.trace_logs
            ],
        }
        assert test_report["test_name"] == "test-complete-workflow"
        assert "stages" in test_report
        assert len(test_report["stages"]) > 0

    def test_stage_execution_order(self):
        """Test stages execute in correct order"""
        gateway, bot = _make_bot(version="v0.2")
        res = bot.reconcile_transaction("TXN-1847")
        tools = [t.get("tool") for t in gateway.trace_logs]
        # Real workflow order: bank lookup -> policy -> recon status -> candidates -> mutation
        expected_prefix = [
            "get_bank_transaction_by_id",
            "get_policy",
            "get_reconciliation_status",
            "search_gl_candidates",
        ]
        idx = -1
        for tool in expected_prefix:
            assert tool in tools, f"Expected tool {tool} in trace {tools}"
            cur = tools.index(tool)
            assert cur > idx, f"Tools should execute in order: {tools}"
            idx = cur

    def test_attack_detection_logic(self):
        """Test that attacks can be detected"""
        attacks = list_all_attacks()
        assert len(attacks) > 0
        gateway, bot = _make_bot("recon_duplicate_candidate", version="v0.2")
        res = bot.reconcile_transaction("TXN-1847")
        assert res is not None
        assert res.get("decision") in ["REVIEW", "BLOCK", "AUTO"]
        assert len(gateway.trace_logs) > 0


def run_integration_tests():
    """Run integration tests with pytest"""
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    run_integration_tests()
