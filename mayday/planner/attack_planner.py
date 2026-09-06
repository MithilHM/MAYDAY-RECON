"""
MAYDAY Attack Planner / Adversary Agent.
Inspects Reliability Memory, prioritizes high-risk and historically weak attack vectors,
and plans targeted adversarial benchmarks.
"""
from typing import Dict, List, Any
from mayday.attacks.attack_registry import list_all_attacks, get_attack_by_id
from mayday.memory.reliability_memory import ReliabilityMemory

class AttackPlannerAgent:
    def __init__(self, memory: ReliabilityMemory):
        self.memory = memory

    def plan_attack_suite(self, suite_type: str = "training") -> List[Dict[str, Any]]:
        all_attacks = list_all_attacks()
        mem_patterns = self.memory.memory.get("failure_patterns", {})

        def severity_weight(attack: Dict[str, Any]) -> float:
            return 1.0 if attack.get("severity") == "CRITICAL" else 0.5

        def scored(attack: Dict[str, Any]) -> Dict[str, Any]:
            aid = attack["id"]
            fail_rate = mem_patterns.get(aid, {}).get("failure_rate", 0.0)
            ranked = dict(attack)
            ranked["priority_score"] = severity_weight(attack) + fail_rate
            return ranked

        # PRD section 19: partition by split field, sort by memory
        # failure_rate + severity. Keeps 20 training / 10 holdout contract.
        if suite_type == "training":
            pool = [a for a in all_attacks if a.get("split", "training") == "training"]
        elif suite_type == "holdout":
            pool = [a for a in all_attacks if a.get("split") == "holdout"]
        else:
            pool = list(all_attacks)

        prioritized = [scored(a) for a in pool]
        prioritized.sort(key=lambda x: x["priority_score"], reverse=True)
        return prioritized
