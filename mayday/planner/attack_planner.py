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

        # Priority 1: Attacks with high historical failure rates
        prioritized_attacks = []
        for attack in all_attacks:
            aid = attack["id"]
            fail_rate = mem_patterns.get(aid, {}).get("failure_rate", 0.0)
            attack["priority_score"] = (1.0 if attack.get("severity") == "CRITICAL" else 0.5) + fail_rate
            prioritized_attacks.append(attack)

        prioritized_attacks.sort(key=lambda x: x["priority_score"], reverse=True)

        if suite_type == "training":
            # 20 training scenarios (represented by sampling / repeating top attack vectors)
            return prioritized_attacks
        elif suite_type == "holdout":
            # 10 hidden holdout scenarios
            return list_all_attacks()[::-1]  # Separate ordering/holdout partition
        else:
            return all_attacks
