"""
MAYDAY Intervention Engine module.
Generates candidate repair interventions (PROMPT, TOOL, WORKFLOW, POLICY, MEMORY),
evaluates candidates empirically against the regression suite, and selects the optimal verified fix.
"""
from typing import Dict, List, Any, Optional

class InterventionEngine:
    def generate_candidates(self, failure_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        missing_behavior = failure_report.get("missing_behavior")
        attack_id = failure_report.get("attack_id")

        candidates = []

        # Candidate A: Prompt Patch Intervention
        candidates.append({
            "id": f"INT-PROMPT-{attack_id}",
            "type": "prompt",
            "name": f"Prompt Patch: Enforce {missing_behavior}",
            "instruction": f"SYSTEM PROMPT: Always check for {missing_behavior} before mutating financial state.",
            "estimated_impact": "PROMPT_ONLY"
        })

        # Candidate B: Verification Tool Intervention
        candidates.append({
            "id": f"INT-TOOL-{attack_id}",
            "type": "tool",
            "name": "Verification Tool: Add Postcondition Verifier",
            "tool": "postcondition_verifier",
            "estimated_impact": "TOOL_VERIFICATION"
        })

        # Candidate C: Workflow Guard Intervention
        candidates.append({
            "id": f"INT-WORKFLOW-{attack_id}",
            "type": "workflow",
            "name": f"Workflow Guard: Add {missing_behavior} Checkpoint",
            "guard": missing_behavior,
            "estimated_impact": "WORKFLOW_CHECKPOINT"
        })

        # Candidate D: Memory Rule Intervention
        candidates.append({
            "id": f"INT-MEMORY-{attack_id}",
            "type": "memory",
            "name": f"Reliability Memory Rule: Remember {missing_behavior}",
            "rule": missing_behavior,
            "estimated_impact": "MEMORY_PATTERNS"
        })

        return candidates

    def select_best_intervention(
        self,
        candidates: List[Dict[str, Any]],
        eval_results_map: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Selects candidate with the highest empirical FAR score on the regression suite.
        """
        best_candidate = None
        best_score = -1.0

        for candidate in candidates:
            score = eval_results_map.get(candidate["id"], 0.0)
            candidate["measured_far_score"] = score
            if score > best_score:
                best_score = score
                best_candidate = candidate

        return best_candidate or candidates[0]
