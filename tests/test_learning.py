"""Learning-loop hardening tests: compound attacks + POLICY intervention guard."""
import pytest
from simulator.seed.seed_data import seed_database
from simulator.db.database import DB_FILE, clear_db
from mayday.gateway.tool_gateway import ToolGateway
from agent.reconbot import ReconBot
from mayday.attacks.attack_registry import get_attack_by_id, get_compound_attack
from mayday.intervention.intervention_engine import InterventionEngine


@pytest.fixture(autouse=True)
def setup_test_db():
    seed_database(DB_FILE)
    yield
    clear_db(DB_FILE)


def test_compound_attack():
    a = get_attack_by_id("recon_duplicate_candidate")
    b = get_attack_by_id("recon_period_boundary")
    assert a and b
    compound = get_compound_attack([a["id"], b["id"]])
    assert compound["id"] == f"compound__{a['id']}__{b['id']}"
    for key in a["setup"]:
        assert key in compound["setup"], f"missing setup key {key} from {a['id']}"
    for key in b["setup"]:
        assert key in compound["setup"], f"missing setup key {key} from {b['id']}"


def test_policy_intervention_blocks():
    attack = get_attack_by_id("recon_duplicate_candidate")
    engine = InterventionEngine()
    candidates = engine.generate_candidates(
        {"attack_id": attack["id"], "missing_behavior": "uniqueness_validation"}
    )
    policy = [c for c in candidates if c.get("type") == "policy"]
    assert len(policy) == 1
    assert "INT-POLICY-" in policy[0]["id"]

    # Baseline v0.1 without guard auto-matches (unsafe).
    seed_database(DB_FILE)
    gw_base = ToolGateway(db_path=DB_FILE, active_attack=attack)
    base_res = ReconBot(gateway=gw_base, version="v0.1").reconcile_transaction("TXN-1847")
    assert base_res["decision"] == "AUTO"

    # v0.1 + POLICY guard must force REVIEW (or BLOCK), never AUTO.
    seed_database(DB_FILE)
    gw = ToolGateway(db_path=DB_FILE, active_attack=attack)
    bot = ReconBot(gateway=gw, version="v0.1", interventions=policy)
    res = bot.reconcile_transaction("TXN-1847")
    assert res["decision"] in ("REVIEW", "BLOCK")
