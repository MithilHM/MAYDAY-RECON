"""
MAYDAY Reliability Memory module.
Persists failure patterns, vulnerability stats, attack success rates, and successful mitigations.
Used by Attack Planner to prioritize adversarial attacks dynamically.
"""
import json
import os
import shutil
import tempfile
import threading
from typing import Dict, List, Any, Optional

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "reliability_memory.json")

_DEFAULT_MEMORY = {
    "failure_patterns": {},
    "successful_mitigations": {},
    "attack_history": [],
    "learned_rules": []
}

_MAX_ATTACK_HISTORY = 1000


def _is_valid_memory(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    for key in ("failure_patterns", "successful_mitigations", "attack_history", "learned_rules"):
        if key not in data:
            return False
    if not isinstance(data["failure_patterns"], dict):
        return False
    if not isinstance(data["successful_mitigations"], dict):
        return False
    if not isinstance(data["attack_history"], list):
        return False
    if not isinstance(data["learned_rules"], list):
        return False
    return True


def _default_memory() -> Dict[str, Any]:
    return {
        "failure_patterns": {},
        "successful_mitigations": {},
        "attack_history": [],
        "learned_rules": []
    }


class ReliabilityMemory:
    def __init__(self, memory_file: str = MEMORY_FILE):
        self.memory_file = memory_file
        self._lock = threading.Lock()
        self.memory: Dict[str, Any] = self.load_memory()

    def load_memory(self) -> Dict[str, Any]:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r") as f:
                    data = json.load(f)
                if _is_valid_memory(data):
                    return data
                # Corrupt / schema-invalid file: back it up and reset.
                try:
                    corrupt_path = self.memory_file + ".corrupt"
                    shutil.copyfile(self.memory_file, corrupt_path)
                except Exception:
                    pass
            except Exception:
                # Unparseable JSON: back up raw bytes for forensics, then reset.
                try:
                    corrupt_path = self.memory_file + ".corrupt"
                    shutil.copyfile(self.memory_file, corrupt_path)
                except Exception:
                    pass
        return _default_memory()

    def save_memory(self):
        with self._lock:
            os.makedirs(os.path.dirname(self.memory_file) or ".", exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                dir=os.path.dirname(self.memory_file) or None,
                prefix=".reliability_memory.",
                suffix=".tmp",
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(self.memory, f, indent=2)
                os.replace(tmp_path, self.memory_file)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                raise

    def record_run(self, attack_id: str, outcome: str, failure_type: Optional[str] = None, mitigation: Optional[Dict[str, Any]] = None):
        with self._lock:
            if attack_id not in self.memory["failure_patterns"]:
                self.memory["failure_patterns"][attack_id] = {
                    "seen": 0,
                    "failures": 0,
                    "success_rate": 0.0,
                    "best_mitigation": None
                }

            entry = self.memory["failure_patterns"][attack_id]
            entry["seen"] += 1
            if outcome == "FAIL":
                entry["failures"] += 1

            entry["failure_rate"] = round(entry["failures"] / entry["seen"], 2)

            if mitigation and outcome == "PASS":
                entry["best_mitigation"] = mitigation.get("name")
                self.memory["successful_mitigations"][attack_id] = mitigation

            self.memory["attack_history"].append({
                "attack_id": attack_id,
                "outcome": outcome,
                "failure_type": failure_type
            })
            # Cap history to last 1000 entries.
            if len(self.memory["attack_history"]) > _MAX_ATTACK_HISTORY:
                self.memory["attack_history"] = self.memory["attack_history"][-_MAX_ATTACK_HISTORY:]

            os.makedirs(os.path.dirname(self.memory_file) or ".", exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                dir=os.path.dirname(self.memory_file) or None,
                prefix=".reliability_memory.",
                suffix=".tmp",
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(self.memory, f, indent=2)
                os.replace(tmp_path, self.memory_file)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                raise

    def get_weak_attack_areas(self) -> List[str]:
        patterns = self.memory.get("failure_patterns", {})
        sorted_attacks = sorted(patterns.items(), key=lambda x: x[1].get("failure_rate", 0.0), reverse=True)
        return [k for k, v in sorted_attacks]

    def attack_success_rates(self) -> Dict[str, float]:
        """Return {attack_id: failure_rate} for all tracked attacks."""
        patterns = self.memory.get("failure_patterns", {})
        rates: Dict[str, float] = {}
        for attack_id, data in patterns.items():
            if isinstance(data, dict):
                if isinstance(data.get("failure_rate"), (int, float)):
                    rates[attack_id] = float(data["failure_rate"])
                else:
                    seen = data.get("seen", 0) or 0
                    fails = data.get("failures", 0) or 0
                    rates[attack_id] = round(fails / seen, 2) if seen else 0.0
            else:
                rates[attack_id] = 0.0
        return rates

    def prioritize_attacks(self, candidate_ids: List[str]) -> List[str]:
        """Sort candidate attack ids by failure_rate desc (riskiest first)."""
        rates = self.attack_success_rates()
        return sorted(candidate_ids, key=lambda aid: rates.get(aid, 0.0), reverse=True)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_attacks_tested": len(self.memory["attack_history"]),
            "tracked_patterns_count": len(self.memory["failure_patterns"]),
            "failure_patterns": self.memory["failure_patterns"],
            "successful_mitigations": self.memory["successful_mitigations"]
        }
