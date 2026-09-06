"""
Unit tests for Advanced Dynamic Cognitive Agentic Architecture in MAYDAY RECON.
Tests:
1. Dynamic Execution Graph (DEG) & ReAct Engine
2. Multi-Tier Cognitive Memory (Working, Episodic, Semantic, Procedural)
3. Dataflow Optimization Pipeline (Dynamic Model Router, AST Pruner, Semantic GL Cache)
"""
import pytest
from mayday.memory.multi_tier_memory import CognitiveMemorySystem, WorkingMemoryScratchpad
from mayday.optimization.dataflow_pipeline import DataflowOptimizationPipeline, DynamicModelRouter, ContextPrunerEngine, SemanticGLCache
from mayday.execution_graph import DynamicExecutionGraphEngine, CognitiveReActEngine, ExecutionGraphNode

def test_multi_tier_memory_system():
    mem = CognitiveMemorySystem()
    wm = mem.create_working_memory("TXN-999")
    wm.record_thought("Testing working memory scratchpad")
    
    assert wm.bank_transaction_id == "TXN-999"
    assert len(wm.thought_history) == 1
    
    pol = mem.semantic.get_policy("POL-001")
    assert pol is not None
    assert pol["category"] == "reconciliation"

    runbook = mem.procedural.get_runbook("postcondition_verifier")
    assert runbook is not None
    assert len(runbook["steps"]) == 6

def test_dynamic_model_router():
    router = DynamicModelRouter()
    
    # Simple deterministic task
    route_t0 = router.route_request("far_score_calc", prompt_tokens=100)
    assert route_t0["model"] == "local_python"
    assert route_t0["cost_inr"] == 0.0

    # Complex ambiguous task
    route_t3 = router.route_request("failure_analysis", prompt_tokens=5000, reasoning_depth=5, is_ambiguous=True, is_db_mutation=True)
    assert route_t3["model"] == "pro"
    assert route_t3["complexity_score"] > 0.70

def test_context_pruner_and_semantic_gl_cache():
    # Context Pruner Test
    raw_payload = {
        "txn_id": "TXN-101",
        "amount": 12450.500001,
        "empty_list": [],
        "null_field": None,
        "nested": {"status": "OK", "empty": ""}
    }
    pruned = ContextPrunerEngine.prune_payload(raw_payload)
    assert "empty_list" not in pruned
    assert "null_field" not in pruned
    assert pruned["amount"] == 12450.50

    # Semantic GL Cache Test
    cache = SemanticGLCache()
    candidates = [{"id": "GL-001", "amount": 500.0}]
    cache.put_candidates(500.0, "BANK-001", candidates)

    cached_res = cache.get_candidates(500.0, "BANK-001")
    assert cached_res == candidates
    assert cache.cache_hits == 1

    cache.invalidate_on_mutation()
    assert cache.get_candidates(500.0, "BANK-001") is None

def test_dynamic_execution_graph():
    deg = DynamicExecutionGraphEngine()
    assert len(deg.execution_order) == 7

    # Inject runtime node
    new_node = ExecutionGraphNode("node_4B", "Stale Refresh", "Refresh stale data", "REFRESH", injected_at_runtime=True)
    deg.inject_node("node_4", new_node)
    
    assert "node_4B" in deg.execution_order
    idx = deg.execution_order.index("node_4")
    assert deg.execution_order[idx + 1] == "node_4B"
