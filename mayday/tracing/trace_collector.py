"""
MAYDAY Trace Collector module.
Constructs and persists structured execution trace records.
"""
import uuid
import json
import time
from typing import Dict, List, Any

class TraceCollector:
    # Snapshots with more tables than this are considered "large" (full dumps)
    # and are NOT duplicated into environment_before/after for perf.
    _SMALL_SNAPSHOT_MAX_TABLES = 3

    @staticmethod
    def _count_rows(state: Any) -> Dict[str, int]:
        if not isinstance(state, dict):
            return {}
        counts: Dict[str, int] = {}
        for table, rows in state.items():
            counts[table] = len(rows) if isinstance(rows, list) else 0
        return counts

    @staticmethod
    def _reconciliation_ids(state: Any) -> List[str]:
        if not isinstance(state, dict):
            return []
        recs = state.get("reconciliations", [])
        if not isinstance(recs, list):
            return []
        return [r.get("id") for r in recs if isinstance(r, dict) and "id" in r]

    @staticmethod
    def _compat_env(state: Any) -> Dict[str, Any]:
        # Backward-compat: keep the full snapshot only if small (light snapshot);
        # otherwise store {} to avoid duplicating the full env. Empty logs -> {}.
        if not isinstance(state, dict) or not state:
            return {}
        if len(state) <= TraceCollector._SMALL_SNAPSHOT_MAX_TABLES:
            return state
        return {}

    @staticmethod
    def create_trace(
        agent_version: str,
        attack_id: str,
        trace_logs: List[Dict[str, Any]],
        eval_result: Dict[str, Any],
        duration_ms: float
    ) -> Dict[str, Any]:
        run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
        env_before_state = trace_logs[0].get("state_before", {}) if trace_logs else {}
        env_after_state = trace_logs[-1].get("state_after", {}) if trace_logs else {}

        # Estimate cost (INR)
        estimated_cost_inr = round(len(trace_logs) * 0.25, 2)

        return {
            "run_id": run_id,
            "agent_version": agent_version,
            "attack_id": attack_id,
            "tool_calls": trace_logs,
            "environment_before": TraceCollector._compat_env(env_before_state),
            "environment_after": TraceCollector._compat_env(env_after_state),
            "environment_before_counts": TraceCollector._count_rows(env_before_state),
            "environment_after_counts": TraceCollector._count_rows(env_after_state),
            "reconciliation_ids": TraceCollector._reconciliation_ids(env_after_state),
            "duration_ms": round(duration_ms, 2),
            "estimated_cost_inr": estimated_cost_inr,
            "decision": eval_result.get("decision"),
            "outcome": eval_result.get("outcome"),
            "financial_exposure": eval_result.get("financial_exposure", 0.0),
            "far_score": eval_result.get("far_score", 0.0),
            "timestamp": time.time()
        }
