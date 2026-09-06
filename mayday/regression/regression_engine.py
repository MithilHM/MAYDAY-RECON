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
