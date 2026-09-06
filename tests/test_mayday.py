"""
Unit and integration tests for MAYDAY RECON platform.
"""
import pytest
import os
from simulator.seed.seed_data import seed_database
from simulator.db.database import get_connection, clear_db, dump_state, DB_FILE
from simulator.services.simulator_service import CFOSimulatorService
from mayday.gateway.tool_gateway import ToolGateway
from agent.reconbot import ReconBot
from mayday.attacks.attack_registry import get_attack_by_id, list_all_attacks
from mayday.evaluator.deterministic_evaluator import DeterministicEvaluator
from mayday.tracing.trace_collector import TraceCollector
from mayday.analyzer.failure_analyzer import FailureAnalyzerAgent
from mayday.regression.regression_engine import RegressionEngine
from mayday.intervention.intervention_engine import InterventionEngine
from mayday.memory.reliability_memory import ReliabilityMemory

@pytest.fixture(autouse=True)
def setup_test_db():
    seed_database(DB_FILE)
    yield
    clear_db(DB_FILE)

def test_cfo_simulator_seeding():
    service = CFOSimulatorService(DB_FILE)
    txns = service.get_bank_transactions()
    assert len(txns) >= 3
    assert txns[0]["id"] == "TXN-1847"
    assert txns[0]["amount"] == 12450.0

def test_tool_gateway_tracing():
    hero_attack = get_attack_by_id("recon_commit_timeout")
    gateway = ToolGateway(db_path=DB_FILE, active_attack=hero_attack)
    bot = ReconBot(gateway=gateway, version="v0.1")
    
    res = bot.reconcile_transaction("TXN-1847")
    assert len(gateway.trace_logs) > 0
    assert gateway.trace_logs[-1]["attack_applied"] == "commit_then_timeout"

def test_deterministic_evaluator():
    hero_attack = get_attack_by_id("recon_commit_timeout")
    gateway = ToolGateway(db_path=DB_FILE, active_attack=hero_attack)
    bot = ReconBot(gateway=gateway, version="v0.1")
    
    res = bot.reconcile_transaction("TXN-1847")
    evaluator = DeterministicEvaluator(hero_attack, gateway.trace_logs, res)
    eval_res = evaluator.evaluate()

    assert "far_score" in eval_res
    assert "outcome" in eval_res

def test_failure_analyzer_and_regression():
    hero_attack = get_attack_by_id("recon_commit_timeout")
    analyzer = FailureAnalyzerAgent()
    report = analyzer.analyze_failure(hero_attack, {}, {"rule_violations": ["TIMEOUT_RETRY_DUPLICATE"]})

    assert report["failure_type"] == "unsafe_mutation_retry"
    assert report["missing_behavior"] == "postcondition_verification"

    reg_engine = RegressionEngine()
    reg = reg_engine.create_regression_test(report, hero_attack)
    assert reg["id"].startswith("MAY-FIN-")

def test_reconbot_v2_recovery():
    hero_attack = get_attack_by_id("recon_commit_timeout")
    gateway = ToolGateway(db_path=DB_FILE, active_attack=hero_attack)
    bot_v2 = ReconBot(gateway=gateway, version="v0.2")

    res = bot_v2.reconcile_transaction("TXN-1847")
    assert res["decision"] == "AUTO"
    assert "Recovered from API timeout" in res["reason"]

def test_refusal_is_pass():
    # RECON-038 self-test: a correct REFUSAL (REVIEW/BLOCK + exception,
    # zero reconciliations) on a must_not-create_reconciliation attack
    # must classify as PASS, not failure.
    seed_database(DB_FILE)
    attack = get_attack_by_id("recon_duplicate_candidate")
    gateway = ToolGateway(db_path=DB_FILE, active_attack=attack)
    bot_v2 = ReconBot(gateway=gateway, version="v0.2")

    res = bot_v2.reconcile_transaction("TXN-1847")
    evaluator = DeterministicEvaluator(attack, gateway.trace_logs, res)
    eval_res = evaluator.evaluate()

    assert res["decision"] in ("REVIEW", "BLOCK")
    assert eval_res["outcome"] == "PASS"
