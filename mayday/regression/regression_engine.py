"""
MAYDAY Regression Engine module.
Converts discovered agent failures into permanent, replayable regression test suites (MAY-FIN-xxx).
"""
import yaml
import os
import time
from typing import Dict, List, Any

REGRESSION_DIR = os.path.join(os.path.dirname(__file__), "generated_regressions")

class RegressionEngine:
    def __init__(self, output_dir: str = REGRESSION_DIR):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.regressions: List[Dict[str, Any]] = []

    def create_regression_test(self, failure_report: Dict[str, Any], attack_spec: Dict[str, Any]) -> Dict[str, Any]:
        regression_id = f"MAY-FIN-{len(self.regressions) + 1:03d}"
        
        regression_spec = {
            "id": regression_id,
            "origin_attack_id": attack_spec.get("id"),
            "failure_type": failure_report.get("failure_type"),
            "root_cause": failure_report.get("root_cause"),
            "severity": failure_report.get("severity"),
            "target": attack_spec.get("target"),
            "setup": attack_spec.get("setup"),
            "expected": attack_spec.get("expected"),
            "missing_behavior_required": failure_report.get("missing_behavior"),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # Save to YAML file
        file_path = os.path.join(self.output_dir, f"{regression_id}.yaml")
        with open(file_path, "w") as f:
            yaml.dump(regression_spec, f, default_flow_style=False)

        self.regressions.append(regression_spec)
        return regression_spec

    def list_all_regressions(self) -> List[Dict[str, Any]]:
        return self.regressions

    def load_regressions(self) -> List[Dict[str, Any]]:
        """Read generated_regressions/*.yaml from disk into memory."""
        import glob
        specs: List[Dict[str, Any]] = []
        for path in sorted(glob.glob(os.path.join(self.output_dir, "*.yaml"))):
            try:
                with open(path, "r") as f:
                    spec = yaml.safe_load(f)
                if spec:
                    specs.append(spec)
            except Exception:
                continue
        self.regressions = specs
        return specs

    def run_regression(
        self,
        regression_spec: Dict[str, Any],
        agent_version: str,
        interventions: List[Dict[str, Any]] = None
    ) -> str:
        """Replay one regression spec through seed -> gateway -> bot -> evaluator.

        Returns "PASS" or "FAIL".
        """
        from simulator.seed.seed_data import seed_database
        from simulator.db.database import DB_FILE
        from mayday.gateway.tool_gateway import ToolGateway
        from agent.reconbot import ReconBot
        from mayday.evaluator.deterministic_evaluator import DeterministicEvaluator

        interventions = interventions or []
        attack_spec = {
            "id": regression_spec.get("origin_attack_id", regression_spec.get("id")),
            "name": regression_spec.get("id"),
            "expected": regression_spec.get("expected", {}),
            "financial_risk": {"amount": 12450.0},
            "target": regression_spec.get("target", {"txn_id": "TXN-1847"}),
            "setup": regression_spec.get("setup", {}),
        }
        seed_database(DB_FILE)
        gateway = ToolGateway(db_path=DB_FILE, active_attack=attack_spec)
        bot = ReconBot(gateway=gateway, version=agent_version,
                       interventions=interventions)
        txn_id = attack_spec["target"].get("txn_id", "TXN-1847")
        try:
            res = bot.reconcile_transaction(txn_id)
        except Exception as e:
            res = {"decision": "BLOCK", "reason": str(e)}
        ev = DeterministicEvaluator(attack_spec, gateway.trace_logs, res).evaluate()
        return ev.get("outcome", "FAIL")

    def minimal_repro(self, attack_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Return the smallest replayable repro for an attack spec."""
        return {
            "txn_id": attack_spec.get("target", {}).get("txn_id", "TXN-1847"),
            "setup": attack_spec.get("setup", {}),
            "expected": attack_spec.get("expected", {}),
            "steps": [
                "get_bank_transaction_by_id",
                "get_policy",
                "get_reconciliation_status",
                "search_gl_candidates",
                "create_reconciliation",
            ],
        }
