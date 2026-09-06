"""
MAYDAY RECON - Core Reconciliation Engine

This engine orchestrates the reconciliation process by:
1. Loading attack definitions from DSL
2. Generating reconciliation scenarios using CFO Simulator
3. Injecting attacks at configured stages
4. Running reconciliation checks
5. Detecting and reporting attack results
"""

import yaml
from typing import Dict, List, Optional
from datetime import datetime
import json
import random

from mayday.agents.reconbot import ReconBot, AttackDefinition, AttackInstance
from simulator.cfo_simulator import CFOSimulator, BankStatement, LedgerEntry


class ReconciliationEngine:
    """
    Core reconciliation engine that drives attack-based testing
    """

    def __init__(self, dsl_path: str = "mayday/attack.dsl.yml"):
        self.reconbot = ReconBot(dsl_path)
        self.simulator = CFOSimulator(bank_name="Acme Financial")
        self.current_session: Optional[Dict] = None
        self.attack_filter: Optional[List[str]] = None
        self.severity_threshold: str = "low"

    def initialize_from_dsl(self, dsl_path: str = "mayday/attack.dsl.yml"):
        """Initialize engine with attack definitions from DSL file"""
        self.reconbot._load_attack_definitions()
        print(f"Reconciliation Engine initialized with {len(self.reconbot.attacks)} attack definitions")

    def run_reconciliation_test(
        self,
        test_name: str,
        attack_filters: Optional[List[str]] = None,
        severity_threshold: str = "low"
    ) -> Dict:
        """
        Run a complete reconciliation test with attack injection

        Args:
            test_name: Unique identifier for the test
            attack_filters: Optional list of attack names to include
            severity_threshold: Minimum severity to apply

        Returns:
            Complete test report
        """
        print(f"\n{'='*60}")
        print(f"Running Reconciliation Test: {test_name}")
        print(f"{'='*60}")

        # Start session
        session = self.reconbot.start_reconciliation_session(
            session_id=f"test-{test_name}",
            attack_filters=attack_filters,
            severity_threshold=severity_threshold
        )

        test_report = {
            "test_name": test_name,
            "test_id": session["session_id"],
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "attacks_enabled": session["attack_count"],
            "attacks": session["attacks"],
            "stages": []
        }

        # Run each stage with optional attack injection
        stages = ["load", "transform", "validate", "match", "report"]

        for stage in stages:
            stage_result = self._run_reconciliation_stage(
                stage=stage,
                test_report=test_report,
                enabled_attacks=session["attacks"]
            )
            test_report["stages"].append(stage_result)

            # Stop if reconciliation failed catastrophically
            if stage_result.get("status") == "failed":
                break

        # End session and generate final report
        session_report = self.reconbot.end_session()

        test_report["end_time"] = datetime.now().isoformat()
        test_report["session_summary"] = session_report["summary"]
        test_report["attacks_reported"] = session_report["attacks"]
        test_report["status"] = "completed" if session_report["summary"]["detected"] > 0 else "completed"

        # Calculate reconciliation metrics
        test_report["metrics"] = self._calculate_metrics(test_report)

        print(f"\n{'='*60}")
        print(f"Test Completed: {test_name}")
        print(f"Total Attacks: {len(session_report['attacks'])}")
        print(f"Detected: {session_report['summary']['detected']}")
        print(f"Resolved: {session_report['summary']['resolved']}")
        print(f"{'='*60}\n")

        return test_report

    def _run_reconciliation_stage(
        self,
        stage: str,
        test_report: Dict,
        enabled_attacks: List[str]
    ) -> Dict:
        """
        Run a single reconciliation stage with attack injection

        Args:
            stage: Reconciliation stage (load, transform, validate, match, report)
            test_report: Test report to update
            enabled_attacks: List of enabled attack names

        Returns:
            Stage execution result
        """
        stage_result = {
            "stage": stage,
            "status": "running",
            "attacks_injected": 0,
            "attacks_detected": 0,
            "transactions_processed": 0
        }

        print(f"\nStage: {stage.upper()}")
        print(f"{'-'*60}")

        # Inject attacks at this stage
        stage_attacks = [a for a in enabled_attacks if self.reconbot.attacks[a].stage == stage]

        if stage_attacks:
            print(f"Injecting {len(stage_attacks)} attacks at {stage} stage")

            for attack_name in stage_attacks:
                try:
                    attack_instance = self.reconbot.inject_attack(
                        attack_name,
                        parameters=self.reconbot.attacks[attack_name].parameters
                    )
                    stage_result["attacks_injected"] += 1

                    # Simulate reconciliation processing
                    transactions_processed = self._process_transactions(stage)

                    print(f"  ✓ Injected: {attack_name} -> {stage_attacks.index(attack_name) + 1}/{len(stage_attacks)}")

                except Exception as e:
                    print(f"  ✗ Error injecting {attack_name}: {e}")

        # Process transactions for this stage
        processed = self._process_transactions(stage)
        stage_result["transactions_processed"] = processed

        # Check for attacks detected
        detected_count = 0
        for attack_id, attack_instance in self.reconbot.attack_instances.items():
            if attack_instance.status == "detected":
                detected_count += 1
                stage_result["attacks_detected"] += 1

        if detected_count > 0:
            print(f"  ⚠ Detected {detected_count} attacks at {stage}")
            stage_result["status"] = "attention_required"
        else:
            stage_result["status"] = "completed"

        return stage_result

    def _process_transactions(self, stage: str) -> int:
        """
        Simulate transaction processing for a given stage

        Args:
            stage: Current reconciliation stage

        Returns:
            Number of transactions processed
        """
        # In a real implementation, this would process actual reconciliation data
        # For simulation, we return a realistic number based on the stage
        stage_processors = {
            "load": random.randint(100, 500),
            "transform": random.randint(100, 500),
            "validate": random.randint(100, 500),
            "match": random.randint(100, 500),
            "report": random.randint(100, 500)
        }

        return stage_processors.get(stage, 0)

    def _calculate_metrics(self, test_report: Dict) -> Dict:
        """Calculate reconciliation metrics from test results"""
        return {
            "total_attacks_injected": len(test_report.get("stages", [])),
            "total_attacks_detected": sum(s.get("attacks_detected", 0) for s in test_report.get("stages", [])),
            "accuracy": round(0.0, 2),  # Would calculate in real implementation
            "performance_score": round(0.0, 2)  # Would calculate in real implementation
        }

    def generate_reconciliation_report(self, test_report: Dict, output_path: Optional[str] = None) -> str:
        """
        Generate human-readable reconciliation report

        Args:
            test_report: Test report to format
            output_path: Optional file path to save report

        Returns:
            Formatted report string
        """
        report_lines = [
            "MAYDAY RECON - Reconciliation Test Report",
            "="*60,
            "",
            f"Test Name: {test_report['test_name']}",
            f"Test ID: {test_report['test_id']}",
            f"Status: {test_report['status']}",
            f"Started: {test_report['start_time']}",
            f"Ended: {test_report['end_time']}",
            "",
            "Session Summary:",
            f"  Total Attacks: {test_report['session_summary']['total_attacks']}",
            f"  Detected: {test_report['session_summary']['detected']}",
            f"  Resolved: {test_report['session_summary']['resolved']}",
            "",
            "Stage Results:",
        ]

        for stage in test_report.get("stages", []):
            status_icon = {
                "running": "🔄",
                "completed": "✅",
                "attention_required": "⚠️",
                "failed": "❌"
            }.get(stage["status"], "❓")

            report_lines.extend([
                f"  {status_icon} {stage['stage'].upper()}:",
                f"     Status: {stage['status']}",
                f"     Attacks Injected: {stage['attacks_injected']}",
                f"     Attacks Detected: {stage['attacks_detected']}",
                f"     Transactions Processed: {stage['transactions_processed']}",
                ""
            ])

        report_lines.extend([
            "Metrics:",
            f"  Total Attacks Injected: {test_report['metrics']['total_attacks_injected']}",
            f"  Total Attacks Detected: {test_report['metrics']['total_attacks_detected']}",
            "="*60
        ])

        report = "\n".join(report_lines)

        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
            print(f"\nReport saved to: {output_path}")

        return report

    def load_dsl(self, dsl_path: str = "mayday/attack.dsl.yml") -> Dict:
        """
        Load DSL file and validate structure

        Args:
            dsl_path: Path to DSL file

        Returns:
            Parsed and validated DSL data
        """
        try:
            with open(dsl_path, 'r') as f:
                dsl_data = yaml.safe_load(f)

            validation = self.reconbot.parse_and_validate_dsl(yaml.dump(dsl_data))

            if validation["valid"]:
                print(f"✓ DSL loaded successfully with {len(dsl_data.get('attacks', []))} attacks")
            else:
                print(f"✗ DSL has errors:")
                for error in validation.get("errors", []):
                    print(f"  - {error}")

            return validation

        except Exception as e:
            print(f"Error loading DSL: {e}")
            return {"valid": False, "errors": [str(e)]}

    def generate_test_suite(self, output_file: str = "test_suite.yaml") -> Dict:
        """
        Generate a test suite from all attack definitions

        Args:
            output_file: Output file path for test suite

        Returns:
            Generated test suite configuration
        """
        test_suite = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "attacks": []
        }

        for attack_name, attack_def in self.reconbot.attacks.items():
            attack_config = {
                "attack_name": attack_name,
                "description": attack_def.description,
                "type": attack_def.type,
                "severity": attack_def.severity,
                "stage": attack_def.stage,
                "method": attack_def.method,
                "parameters": attack_def.parameters,
                "tags": attack_def.tags
            }
            test_suite["attacks"].append(attack_config)

        # Write to file
        with open(output_file, 'w') as f:
            yaml.dump(test_suite, f, default_flow_style=False, sort_keys=False)

        print(f"Generated test suite with {len(test_suite['attacks'])} attacks")
        return test_suite


# Example usage and test
if __name__ == "__main__":
    # Initialize engine
    engine = ReconciliationEngine()
    engine.initialize_from_dsl()

    # Run a standard reconciliation test
    test_report = engine.run_reconciliation_test(
        test_name="test-standard-transactions",
        attack_filters=["transaction_fraud"],
        severity_threshold="medium"
    )

    # Generate report
    report = engine.generate_reconciliation_report(test_report)

    # Generate test suite
    test_suite = engine.generate_test_suite()

    # Run another test with different attack
    print("\n" + "="*60)
    test_report2 = engine.run_reconciliation_test(
        test_name="test-GL-mismatch-detection",
        attack_filters=["GL_mismatch"],
        severity_threshold="high"
    )

    report2 = engine.generate_reconciliation_report(test_report2, "report2.txt")
