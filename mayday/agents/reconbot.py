"""
MAYDAY RECON - ReconBot Agent Implementation

The ReconBot is the primary orchestration agent that:
1. Loads and parses attack definitions from the DSL
2. Coordinates attack injection during reconciliation runs
3. Monitors for attack detection and reporting
4. Manages reconciliation session lifecycle
"""

import json
import yaml
from typing import Dict, List, Optional
from datetime import datetime
import hashlib
from dataclasses import dataclass, field
import threading
import time


@dataclass
class AttackDefinition:
    """Represents a single attack definition from the DSL"""
    name: str = ""
    description: str = ""
    type: str = ""
    severity: str = "medium"
    enabled: bool = True
    parameters: Dict = field(default_factory=dict)
    stage: str = "load"
    method: str = "default"
    target: str = "all"
    detection: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    how_to_apply: Optional[str] = None
    expected_failure: Optional[str] = None

    def validate(self) -> List[str]:
        """Validate attack definition against schema"""
        errors = []
        if not self.name:
            errors.append("name is required")
        if self.severity not in ["low", "medium", "high", "critical"]:
            errors.append(f"invalid severity: {self.severity}")
        return errors


@dataclass
class AttackInstance:
    """Runtime representation of an active attack"""
    id: str
    definition: AttackDefinition
    status: str = "pending"  # pending, active, detected, resolved, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    injection_result: Optional[Dict] = None

    @property
    def attack_id(self) -> str:
        """Alias for id (legacy test compatibility)."""
        return self.id

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.definition.name,
            "type": self.definition.type,
            "severity": self.definition.severity,
            "stage": self.definition.stage,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "injection_result": self.injection_result
        }


class ReconBot:
    """Main orchestration agent for attack-driven reconciliation testing"""

    def __init__(self, dsl_path: str = "mayday/attack.dsl.yml"):
        self.dsl_path = dsl_path
        self.attacks: Dict[str, AttackDefinition] = {}
        self.attack_instances: Dict[str, AttackInstance] = {}
        self.session_id: Optional[str] = None
        self.active_attacks: bool = False
        self.reconciliation_state: Dict = {}
        self.lock = threading.Lock()

        self._load_attack_definitions()

    @staticmethod
    def _normalize_attack_config(attack_config: Dict) -> Dict:
        """Accept legacy DSL, verbose DSL, and PRD S11 (id/workflow/setup/expected) entries."""
        cfg = dict(attack_config)
        if "id" in cfg and "name" not in cfg:
            cfg["name"] = cfg["id"]
        if "id" in cfg and "type" not in cfg:
            # PRD S11 format -> map onto legacy AttackDefinition fields.
            expected = cfg.get("expected", {}) or {}
            must = expected.get("must", []) or []
            target = cfg.get("target", {})
            target_str = target.get("txn_id", "bank_statement.transactions") if isinstance(target, dict) else str(target)
            return {
                "name": cfg.get("name", cfg.get("id", "unknown")),
                "description": cfg.get("description", cfg.get("name", "")),
                "type": "transaction_fraud",
                "severity": str(cfg.get("severity", "medium")).lower(),
                "enabled": True,
                "parameters": cfg.get("setup", {}),
                "stage": "match",
                "method": "mutate",
                "target": str(target_str),
                "detection": ",".join(must),
                "tags": [],
            }
        # Legacy/verbose DSL: pick known keys, derive stage/method/target.
        how = cfg.get("how_to_apply", {}) or {}
        exp_fail = cfg.get("expected_failure", {}) or {}
        return {
            "name": cfg.get("name", cfg.get("id", "unknown")),
            "description": cfg.get("description", ""),
            "type": cfg.get("type", "transaction_fraud"),
            "severity": str(cfg.get("severity", "medium")).lower(),
            "enabled": cfg.get("enabled", True),
            "parameters": cfg.get("parameters", cfg.get("setup", {})),
            "stage": how.get("stage", cfg.get("stage", "match")),
            "method": how.get("method", cfg.get("method", "mutate")),
            "target": str(how.get("target", cfg.get("target", ""))),
            "detection": exp_fail.get("detection", cfg.get("detection", "")),
            "tags": cfg.get("tags", []),
        }

    def _load_attack_definitions(self):
        """Load and parse attack definitions from DSL file"""
        try:
            with open(self.dsl_path, 'r') as f:
                dsl_data = yaml.safe_load(f)

            version = dsl_data.get('version', '1.0')
            attack_list = dsl_data.get('attacks', [])

            for attack_config in attack_list:
                attack = AttackDefinition(**self._normalize_attack_config(attack_config))
                validation_errors = attack.validate()

                if validation_errors:
                    print(f"Warning: Invalid attack '{attack.name}':")
                    for error in validation_errors:
                        print(f"  - {error}")
                else:
                    self.attacks[attack.name] = attack
                    print(f"Loaded attack definition: {attack.name} ({attack.type})")

            print(f"Loaded {len(self.attacks)} valid attack definitions")

        except FileNotFoundError:
            print(f"Error: DSL file not found at {self.dsl_path}")
            self.attacks = {}
        except Exception as e:
            print(f"Error loading DSL: {e}")

    def start_reconciliation_session(
        self,
        session_id: str,
        attack_filters: Optional[List[str]] = None,
        severity_threshold: str = "low"
    ) -> Dict:
        """
        Start a new reconciliation session with optional attack filter

        Args:
            session_id: Unique session identifier
            attack_filters: Optional list of attack names to enable
            severity_threshold: Minimum severity to apply

        Returns:
            Session initialization result
        """
        with self.lock:
            self.session_id = session_id
            self.active_attacks = True
            self.reconciliation_state = {
                "session_id": session_id,
                "started_at": datetime.now().isoformat(),
                "stage": "initializing",
                "status": "active"
            }

            # Filter attacks based on parameters
            enabled_attacks = []
            for name, attack in self.attacks.items():
                if not attack.enabled:
                    continue

                if attack_filters and name not in attack_filters:
                    continue

                if attack.severity < severity_threshold:
                    continue

                enabled_attacks.append(name)

            self.active_attack_names = enabled_attacks
            print(f"Session {session_id}: Starting with {len(enabled_attacks)} attacks")

            return {
                "session_id": session_id,
                "status": "active",
                "attack_count": len(enabled_attacks),
                "attacks": enabled_attacks
            }

    def inject_attack(self, attack_name: str, parameters: Optional[Dict] = None) -> AttackInstance:
        """
        Inject a specific attack into the reconciliation pipeline

        Args:
            attack_name: Name of attack from DSL
            parameters: Override parameters from DSL defaults

        Returns:
            Attack instance for monitoring
        """
        with self.lock:
            if attack_name not in self.attacks:
                raise ValueError(f"Attack '{attack_name}' not found")

            attack_def = self.attacks[attack_name]

            # Create attack instance
            attack_id = self._generate_attack_id(attack_name)
            attack_instance = AttackInstance(
                id=attack_id,
                definition=attack_def
            )

            self.attack_instances[attack_id] = attack_instance

            # Simulate attack injection
            print(f"Injecting attack: {attack_name} -> {attack_def.stage} / {attack_def.method} -> {attack_def.target}")

            # Update state based on attack type and parameters
            self._apply_attack(attack_instance, parameters)

            return attack_instance

    def _apply_attack(self, instance: AttackInstance, parameters: Optional[Dict]):
        """Apply attack logic based on type and stage"""
        attack = instance.definition

        # Record injection start
        instance.start_time = datetime.now()
        instance.status = "active"

        # Simulate injection based on attack parameters
        # In real implementation, this would interact with reconciliation data
        injection_data = {
            "attack_id": instance.id,
            "stage": attack.stage,
            "method": attack.method,
            "target": attack.target,
            "parameters": parameters or attack.parameters,
            "timestamp": datetime.now().isoformat()
        }

        instance.injection_result = injection_data

        # Update reconciliation state based on stage
        if attack.stage == "load":
            self.reconciliation_state["load_stage_status"] = "ATTACK_INJECTED"

        elif attack.stage == "transform":
            if attack.method == "mutate" and "amount_range" in attack.parameters:
                self.reconciliation_state["transform_mutations"] = self.reconciliation_state.get("transform_mutations", 0) + 1

        elif attack.stage == "validate":
            if attack.method == "drop":
                self.reconciliation_state["dropped_valid_records"] = self.reconciliation_state.get("dropped_valid_records", 0) + 1

        elif attack.stage == "match":
            if attack.method == "duplicate":
                self.reconciliation_state["duplicate_records"] = self.reconciliation_state.get("duplicate_records", 0) + 1

        elif attack.stage == "report":
            self.reconciliation_state["report_stage_status"] = "ATTACK_REPORTED"

    def _generate_attack_id(self, name: str) -> str:
        """Generate unique attack instance identifier"""
        timestamp = int(time.time() * 1000)
        hash_suffix = hashlib.md5(f"{name}_{timestamp}".encode()).hexdigest()[:8]
        return f"attack_{hash_suffix}"

    def get_attack_status(self, attack_id: str) -> Optional[Dict]:
        """Get current status of an attack instance"""
        with self.lock:
            if attack_id not in self.attack_instances:
                return None

            instance = self.attack_instances[attack_id]

            # Simulate detection check
            if instance.status == "active":
                instance.status = "detected" if self._simulate_detection(instance) else "active"

            return instance.to_dict()

    def _simulate_detection(self, instance: AttackInstance) -> bool:
        """Simulate detection of attack based on type and parameters"""
        attack = instance.definition

        # Higher severity attacks have higher detection probability
        severity_map = {"low": 0.7, "medium": 0.85, "high": 0.95, "critical": 1.0}

        detection_prob = severity_map.get(attack.severity, 0.5)

        # Detection is more likely if no specific detection method defined
        if not attack.detection:
            detection_prob *= 0.8

        import random
        return random.random() < detection_prob

    def end_session(self, resolution: Optional[Dict] = None) -> Dict:
        """
        End reconciliation session and generate report

        Args:
            resolution: Resolution details including detected attacks

        Returns:
            Session summary report
        """
        with self.lock:
            if not self.session_id:
                return {"error": "No active session"}

            session_report = {
                "session_id": self.session_id,
                "ended_at": datetime.now().isoformat(),
                "status": "complete",
                "resolution": resolution or {},
                "attacks": [
                    instance.to_dict() for instance in self.attack_instances.values()
                ],
                "summary": {
                    "total_attacks": len(self.attack_instances),
                    "detected": sum(1 for i in self.attack_instances.values() if i.status == "detected"),
                    "resolved": sum(1 for i in self.attack_instances.values() if i.status == "resolved")
                }
            }

            # Reset state
            self.session_id = None
            self.active_attacks = False
            self.attack_instances = {}

            return session_report

    def get_session_report(self) -> Dict:
        """Get current session report"""
        with self.lock:
            if not self.session_id:
                return {"error": "No active session"}

            return {
                **self.reconciliation_state,
                "active_attacks": self.active_attack_names,
                "status": "running"
            }

    def parse_and_validate_dsl(self, dsl_content: str) -> Dict:
        """
        Parse and validate DSL content without loading from file

        Args:
            dsl_content: Raw DSL YAML content

        Returns:
            Validation results and parsed attacks
        """
        try:
            dsl_data = yaml.safe_load(dsl_content)

            validation_result = {
                "valid": True,
                "errors": [],
                "attacks": []
            }

            if not isinstance(dsl_data, dict):
                validation_result["valid"] = False
                validation_result["errors"].append("DSL must be a dictionary")
                return validation_result

            version = dsl_data.get('version', '1.0')
            attack_list = dsl_data.get('attacks', [])

            for i, attack_config in enumerate(attack_list):
                attack = AttackDefinition(**self._normalize_attack_config(attack_config))
                validation_errors = attack.validate()

                validation_result["attacks"].append({
                    "index": i,
                    "name": attack.name,
                    "valid": len(validation_errors) == 0,
                    "errors": validation_errors
                })

                if validation_errors:
                    validation_result["valid"] = False
                    validation_result["errors"].extend([f"Attack {i}: {e}" for e in validation_errors])

            return validation_result

        except yaml.YAMLError as e:
            return {
                "valid": False,
                "errors": [f"YAML parsing error: {e}"]
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Error parsing DSL: {e}"]
            }


# Example usage and test
if __name__ == "__main__":
    # Initialize ReconBot
    bot = ReconBot()

    # Start a reconciliation session
    session = bot.start_reconciliation_session(
        session_id="demo-session-1",
        attack_filters=["transaction_fraud"],
        severity_threshold="medium"
    )

    print(f"\nSession started: {session}")

    # Inject attacks
    for attack_name in bot.active_attack_names:
        attack_id = bot._generate_attack_id(attack_name)
        attack_instance = bot.inject_attack(attack_name)

        # Simulate running reconciliation stages
        for _ in range(10):  # Simulate 10 reconciliation iterations
            time.sleep(0.1)  # Simulate processing time

            # Check detection status
            status = bot.get_attack_status(attack_id)
            if status and status.get("status") == "detected":
                print(f"⚠️  Attack detected: {status['name']}")
                break

    # End session and generate report
    report = bot.end_session()
    print(f"\nSession Report:\n{json.dumps(report, indent=2)}")
