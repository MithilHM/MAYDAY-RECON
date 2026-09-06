"""
MAYDAY Trace Collector module.
Constructs and persists structured execution trace records.
"""
import uuid
import json
import time
from typing import Dict, List, Any

class TraceCollector:
    @staticmethod
    def create_trace(
        agent_version: str,
        attack_id: str,
        trace_logs: List[Dict[str, Any]],
        eval_result: Dict[str, Any],
        duration_ms: float
    ) -> Dict[str, Any]:
        run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
        env_before = trace_logs[0]["state_before"] if trace_logs else {}
        env_after = trace_logs[-1]["state_after"] if trace_logs else {}

        # Estimate cost (INR)
        estimated_cost_inr = round(len(trace_logs) * 0.25, 2)

        return {
            "run_id": run_id,
            "agent_version": agent_version,
            "attack_id": attack_id,
            "tool_calls": trace_logs,
            "environment_before": env_before,
            "environment_after": env_after,
            "duration_ms": round(duration_ms, 2),
            "estimated_cost_inr": estimated_cost_inr,
            "decision": eval_result.get("decision"),
            "outcome": eval_result.get("outcome"),
            "financial_exposure": eval_result.get("financial_exposure", 0.0),
            "far_score": eval_result.get("far_score", 0.0),
            "timestamp": time.time()
        }
