"""
Cost & Efficiency Optimized Dataflow Pipeline for MAYDAY RECON & ReconBot.
Implements:
1. Dynamic Tiered Model Router (Tier 0 Local -> Tier 1 Light -> Tier 2 Mid -> Tier 3 Pro)
2. Payload AST Pruner & Context Compression Engine
3. L1 Exact & L2 Semantic GL Cache Layer with Mutation Invalidation
"""
import hashlib
import json
import time
from typing import Dict, List, Any, Optional

# -----------------------------------------------------------------------------
# 1. Dynamic Tiered Model Router
# -----------------------------------------------------------------------------

class DynamicModelRouter:
    """
    Routes requests to appropriate model Tiers (Tier 0 to Tier 3)
    based on Complexity Score C(R).
    """
    def __init__(self):
        self.routing_logs: List[Dict[str, Any]] = []

    def compute_complexity_score(
        self,
        prompt_tokens: int,
        reasoning_depth: int,
        is_ambiguous: bool,
        is_db_mutation: bool
    ) -> float:
        s_tokens = min(1.0, prompt_tokens / 4000.0)
        s_depth = min(1.0, reasoning_depth / 5.0)
        s_ambiguity = 1.0 if is_ambiguous else 0.2
        s_risk = 1.0 if is_db_mutation else 0.1

        complexity_score = (0.2 * s_tokens + 0.3 * s_depth + 0.3 * s_ambiguity + 0.2 * s_risk)
        return round(complexity_score, 3)

    def route_request(
        self,
        task_name: str,
        prompt_tokens: int = 500,
        reasoning_depth: int = 1,
        is_ambiguous: bool = False,
        is_db_mutation: bool = False
    ) -> Dict[str, Any]:
        c_score = self.compute_complexity_score(prompt_tokens, reasoning_depth, is_ambiguous, is_db_mutation)

        if c_score == 0.0 or task_name in ["deterministic_evaluation", "far_score_calc"]:
            tier = "Tier 0 (Local Python Engine)"
            model = "local_python"
            cost_inr = 0.0
            sla_ms = 5.0
        elif c_score <= 0.35:
            tier = "Tier 1 (Light Fast Model)"
            model = "flash_lite"
            cost_inr = 0.05
            sla_ms = 250.0
        elif c_score <= 0.70:
            tier = "Tier 2 (Balanced Model)"
            model = "flash"
            cost_inr = 0.20
            sla_ms = 600.0
        else:
            tier = "Tier 3 (High-Reasoning Model)"
            model = "pro"
            cost_inr = 1.25
            sla_ms = 2000.0

        record = {
            "task_name": task_name,
            "complexity_score": c_score,
            "tier": tier,
            "model": model,
            "cost_inr": cost_inr,
            "sla_ms": sla_ms,
            "timestamp": time.time()
        }
        self.routing_logs.append(record)
        return record

# -----------------------------------------------------------------------------
# 2. Context Pruner & Payload Compression Engine
# -----------------------------------------------------------------------------

class ContextPrunerEngine:
    @staticmethod
    def prune_payload(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Strips null values, trims decimals to 2 places, and projects core schema attributes."""
        if not isinstance(raw_data, dict):
            return raw_data

        pruned = {}
        for key, val in raw_data.items():
            if val is None or val == [] or val == "":
                continue  # Eliminate empty/null fields
            
            if isinstance(val, float):
                pruned[key] = round(val, 2)  # Reduce currency floating precision
            elif isinstance(val, dict):
                pruned[key] = ContextPrunerEngine.prune_payload(val)
            elif isinstance(val, list):
                pruned[key] = [ContextPrunerEngine.prune_payload(item) if isinstance(item, dict) else item for item in val]
            else:
                pruned[key] = val

        return pruned

    @staticmethod
    def compress_sliding_window_history(turns: List[Dict[str, Any]], max_turns: int = 3) -> Dict[str, Any]:
        """Compresses long execution trace history into a high-level summary + recent turns."""
        if len(turns) <= max_turns:
            return {"summary": "Short trace history", "turns": turns}

        old_turns = turns[:-max_turns]
        recent_turns = turns[-max_turns:]

        summary_actions = [f"Step {t.get('step_index', idx)}: {t.get('tool_name', 'tool')} -> {t.get('status', 'OK')}" for idx, t in enumerate(old_turns)]
        
        return {
            "summary": f"Executed {len(old_turns)} prior steps: " + "; ".join(summary_actions),
            "recent_turns": recent_turns
        }

# -----------------------------------------------------------------------------
# 3. Semantic General Ledger (GL) Cache Layer
# -----------------------------------------------------------------------------

class SemanticGLCache:
    """
    L1 Exact Key Match + L2 Semantic Fuzzy Match cache for GL query candidate sets.
    Features mutation-aware invalidation on DB commits.
    """
    def __init__(self):
        self.l1_exact_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.l2_semantic_cache: List[Dict[str, Any]] = []
        self.cache_hits = 0
        self.cache_misses = 0

    def _hash_key(self, amount: float, account_id: str) -> str:
        raw = f"{amount:.2f}_{account_id}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def get_candidates(self, amount: float, account_id: str = "BANK-001") -> Optional[List[Dict[str, Any]]]:
        key = self._hash_key(amount, account_id)
        
        # L1 Exact Cache Check
        if key in self.l1_exact_cache:
            self.cache_hits += 1
            return self.l1_exact_cache[key]

        # L2 Semantic Fuzzy Cache Check (Amount tolerance +/- 0.01)
        for item in self.l2_semantic_cache:
            if abs(item["amount"] - amount) < 0.01 and item["account_id"] == account_id:
                self.cache_hits += 1
                return item["candidates"]

        self.cache_misses += 1
        return None

    def put_candidates(self, amount: float, account_id: str, candidates: List[Dict[str, Any]]):
        key = self._hash_key(amount, account_id)
        self.l1_exact_cache[key] = candidates
        self.l2_semantic_cache.append({
            "amount": amount,
            "account_id": account_id,
            "candidates": candidates,
            "timestamp": time.time()
        })

    def invalidate_on_mutation(self):
        """Mutation-aware cache invalidation triggered on database writes."""
        self.l1_exact_cache.clear()
        self.l2_semantic_cache.clear()

# -----------------------------------------------------------------------------
# Unified Dataflow Pipeline Coordinator
# -----------------------------------------------------------------------------

class DataflowOptimizationPipeline:
    def __init__(self):
        self.router = DynamicModelRouter()
        self.pruner = ContextPrunerEngine()
        self.gl_cache = SemanticGLCache()

    def get_stats(self) -> Dict[str, Any]:
        total_cache = self.gl_cache.cache_hits + self.gl_cache.cache_misses
        hit_rate = round((self.gl_cache.cache_hits / total_cache * 100), 1) if total_cache > 0 else 0.0
        return {
            "cache_hits": self.gl_cache.cache_hits,
            "cache_misses": self.gl_cache.cache_misses,
            "hit_rate_pct": hit_rate,
            "routed_requests_count": len(self.router.routing_logs)
        }
