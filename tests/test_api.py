"""API tests for MAYDAY RECON dashboard (live benchmark data)."""
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_attacks_returns_all_classes():
    res = client.get("/api/attacks")
    assert res.status_code == 200
    attacks = res.json()
    assert isinstance(attacks, list)
    assert len(attacks) >= 12


def test_overview_has_version_metrics():
    res = client.get("/api/overview")
    assert res.status_code == 200
    data = res.json()
    for key in (
        "target_agent",
        "reliability_score",
        "adversarial_reliability",
        "recovery_rate",
        "policy_compliance",
        "unsafe_mutations",
        "cost_per_task_inr",
        "latency_seconds",
        "v1_metrics",
        "v2_metrics",
    ):
        assert key in data, f"missing overview key: {key}"
    assert "average_far_score" in data["v1_metrics"]
    assert "average_far_score" in data["v2_metrics"]


def test_evolution_has_versions():
    res = client.get("/api/evolution")
    assert res.status_code == 200
    data = res.json()
    assert "versions" in data
    assert isinstance(data["versions"], list)
    assert len(data["versions"]) >= 2
    assert "holdout" in data
    assert "memory" in data


def test_memory_has_failure_patterns():
    res = client.post("/api/attacks/recon_commit_timeout/run?agent_version=v0.1")
    assert res.status_code == 200
    res = client.get("/api/memory")
    assert res.status_code == 200
    data = res.json()
    assert "failure_patterns" in data
