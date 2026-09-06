"""
Multi-Tier Cognitive Memory Architecture for ReconBot & MAYDAY RECON.
Provides unified interfaces for Episodic, Semantic, Working, and Procedural Memory Tiers.
Ref: docs/memory_layer_design.md
"""

from typing import Dict, List, Any, Optional
import json
import os
import time
from datetime import datetime
from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# 1. Working Memory (Scratchpad / In-Flight Context & Tool Call Budget)
# -----------------------------------------------------------------------------

class WorkingMemoryScratchpad(BaseModel):
    bank_transaction_id: str
    current_transaction: Optional[Dict[str, Any]] = None
    active_policy: Optional[Dict[str, Any]] = None
    retrieved_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    ambiguity_flag: bool = False
    stale_data_flag: bool = False
    cross_period_flag: bool = False
    cross_currency_flag: bool = False
    pending_exceptions: List[Dict[str, Any]] = Field(default_factory=list)
    tool_calls_count: int = 0
    in_flight_mutation: Optional[Dict[str, Any]] = None
    thought_history: List[str] = Field(default_factory=list)
    flags: Dict[str, bool] = Field(default_factory=lambda: {
        "ambiguity": False,
        "stale": False,
        "cross_period": False,
        "fx_mismatch": False
    })

    def record_thought(self, thought: str):
        self.thought_history.append(f"[{time.strftime('%H:%M:%S')}] {thought}")

    def increment_tool_calls(self) -> int:
        self.tool_calls_count += 1
        return self.tool_calls_count

    def add_candidate(self, candidate: Dict[str, Any]):
        self.retrieved_candidates.append(candidate)

    def record_exception(self, reason: str, severity: str):
        self.pending_exceptions.append({
            "bank_transaction_id": self.bank_transaction_id,
            "reason": reason,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        })

    def clear(self):
        self.current_transaction = None
        self.active_policy = None
        self.retrieved_candidates.clear()
        self.ambiguity_flag = False
        self.stale_data_flag = False
        self.cross_period_flag = False
        self.cross_currency_flag = False
        self.pending_exceptions.clear()
        self.tool_calls_count = 0
        self.in_flight_mutation = None
        self.thought_history.clear()
        self.flags = {
            "ambiguity": False,
            "stale": False,
            "cross_period": False,
            "fx_mismatch": False
        }


# Alias for spec backward compatibility
WorkingMemory = WorkingMemoryScratchpad


# -----------------------------------------------------------------------------
# 2. Episodic Memory (Trace Records, Environment Snapshots & Diffs)
# -----------------------------------------------------------------------------

class ToolCallRecord(BaseModel):
    step_index: int
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EnvironmentStateSnapshot(BaseModel):
    bank_transaction_status: str = "UNRECONCILED"
    reconciliation_records_count: int = 0
    audit_log_entries_count: int = 0
    gl_entry_statuses: Dict[str, str] = Field(default_factory=dict)


class EpisodicTraceRecord(BaseModel):
    trace_id: str
    agent_version: str
    attack_id: str
    bank_transaction_id: str
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    state_before: Optional[EnvironmentStateSnapshot] = None
    state_after: Optional[EnvironmentStateSnapshot] = None
    final_decision: Dict[str, Any] = Field(default_factory=dict)
    far_score: float = 0.0
    outcome: str = "PASS"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EpisodicMemoryStore:
    def __init__(self, trace_dir: str = os.path.join(os.path.dirname(__file__), "traces")):
        self.trace_dir = trace_dir
        os.makedirs(self.trace_dir, exist_ok=True)
        self.traces: List[Dict[str, Any]] = []

    def record_trace(self, trace_data: Dict[str, Any]) -> str:
        trace_id = trace_data.get("trace_id", f"TRACE-{int(time.time())}")
        file_path = os.path.join(self.trace_dir, f"{trace_id}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(trace_data, f, indent=2)
        except Exception:
            pass
        self.traces.append(trace_data)
        return file_path

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        file_path = os.path.join(self.trace_dir, f"{trace_id}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        for tr in self.traces:
            if tr.get("trace_id") == trace_id or tr.get("run_id") == trace_id:
                return tr
        return None

    def record_episode(self, trace_record: Dict[str, Any]):
        self.record_trace(trace_record)

    def get_episode_by_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self.get_trace(run_id)


# -----------------------------------------------------------------------------
# 3. Semantic Memory (Policy Rules, Accounting Standards, Vulnerability Taxonomy)
# -----------------------------------------------------------------------------

class PolicyRule(BaseModel):
    rule_id: str
    category: str
    max_auto_reconcile_amount: float
    rule_text: str
    severity_on_violation: str = "HIGH"


class FailurePattern(BaseModel):
    attack_id: str
    seen: int = 0
    failures: int = 0
    failure_rate: float = 0.0
    best_mitigation: Optional[str] = None


class ReliabilityMemorySchema(BaseModel):
    failure_patterns: Dict[str, FailurePattern] = Field(default_factory=dict)
    successful_mitigations: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    attack_history: List[Dict[str, Any]] = Field(default_factory=list)
    learned_rules: List[str] = Field(default_factory=list)


class SemanticMemoryStore:
    def __init__(self, memory_file: str = os.path.join(os.path.dirname(__file__), "reliability_memory.json")):
        self.memory_file = memory_file
        self.data = self._load()
        self.policies: Dict[str, Dict[str, Any]] = {
            "POL-001": {
                "id": "POL-001",
                "category": "reconciliation",
                "max_auto_reconcile_amount": 100000.0,
                "rule_text": "Auto-reconcile transactions under INR 1,00,000. Escalation required for ambiguity or stale ledger data."
            },
            "POL-002": {
                "id": "POL-002",
                "category": "escalation",
                "max_auto_reconcile_amount": 100000.0,
                "rule_text": "High-value transactions over INR 1,00,000 require mandatory REVIEW."
            }
        }
        self.vulnerability_taxonomy: Dict[str, str] = {
            "recon_commit_timeout": "unsafe_mutation_retry: timeout interpreted as failure without postcondition verification",
            "recon_duplicate_candidate": "ambiguous_candidate_resolution: selecting candidate[0] without uniqueness validation",
            "recon_stale_gl": "stale_data_reconciliation: auto-reconciling unverified stale ledger entries",
            "recon_cross_currency_mismatch": "currency_conversion_error: matching USD and INR without currency check"
        }

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "failure_patterns": {},
            "successful_mitigations": {},
            "attack_history": [],
            "learned_rules": []
        }

    def save(self):
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

    def get_learned_rules(self) -> List[str]:
        return self.data.get("learned_rules", [])

    def record_pattern(self, attack_id: str, outcome: str, mitigation: Optional[Dict[str, Any]] = None):
        patterns = self.data.setdefault("failure_patterns", {})
        if attack_id not in patterns:
            patterns[attack_id] = {"seen": 0, "failures": 0, "failure_rate": 0.0}
        
        patterns[attack_id]["seen"] += 1
        if outcome == "FAIL":
            patterns[attack_id]["failures"] += 1
        patterns[attack_id]["failure_rate"] = round(patterns[attack_id]["failures"] / patterns[attack_id]["seen"], 2)

        if mitigation and outcome == "PASS":
            self.data.setdefault("successful_mitigations", {})[attack_id] = mitigation

        self.save()

    def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        return self.policies.get(policy_id)

    def search_policies_by_amount(self, amount: float) -> List[Dict[str, Any]]:
        matching = []
        for p in self.policies.values():
            if amount > p.get("max_auto_reconcile_amount", 100000.0):
                matching.append(p)
        return matching


# -----------------------------------------------------------------------------
# 4. Procedural Memory (Runbooks & Postcondition Verification Procedures)
# -----------------------------------------------------------------------------

class VerificationProcedure(BaseModel):
    procedure_name: str
    trigger_error: str = "TimeoutError"
    verification_tool: str = "get_reconciliation_status"
    success_action: str = "TIMEOUT_RECOVERY_VERIFIED"
    failure_action: str = "BLOCK"


class ProceduralRunbook(BaseModel):
    runbook_id: str
    agent_version: str
    steps: List[str]
    has_postcondition_verifier: bool = True
    has_policy_guard: bool = True
    active_workflow_guards: List[str] = Field(default_factory=list)


class ProceduralMemoryStore:
    def __init__(self):
        self.procedures: Dict[str, Any] = {
            "postcondition_verifier": self.verify_postcondition_after_timeout,
            "escalation_decision": self.evaluate_escalation_tier
        }
        self.runbooks: Dict[str, Dict[str, Any]] = {
            "postcondition_verifier": {
                "name": "Idempotent Postcondition Verification Protocol",
                "steps": [
                    "1. Record Pre-Mutation State Snapshot",
                    "2. Attempt DB Mutation via Gateway Proxy",
                    "3. Intercept Network / Gateway Timeout Error",
                    "4. Issue Non-Mutating Query (get_reconciliation_status)",
                    "5. If Record Exists -> Verify DB State & Proceed with AUTO",
                    "6. If Record Missing -> Safely Issue Retry"
                ]
            },
            "uniqueness_gate": {
                "name": "Candidate Set Ambiguity Verification",
                "steps": [
                    "1. Search GL Candidates matching amount",
                    "2. If len(candidates) > 1 -> Mark Ambiguity Flag",
                    "3. Create Exception & Escalate Decision to REVIEW"
                ]
            }
        }

    def verify_postcondition_after_timeout(self, gateway: Any, bank_txn_id: str) -> Optional[Dict[str, Any]]:
        """
        Executes postcondition verification workflow following API timeout.
        Prevents duplicate financial mutations by inspecting DB status directly.
        """
        status = gateway.call_tool("get_reconciliation_status", {"bank_transaction_id": bank_txn_id})
        if status and isinstance(status, dict) and status.get("id"):
            gateway.call_tool("write_audit_event", {
                "entity_type": "reconciliation",
                "entity_id": status["id"],
                "action": "TIMEOUT_RECOVERY_VERIFIED",
                "performed_by": "ProceduralMemory_PostconditionVerifier",
                "details": "Verified DB transaction state following API timeout error."
            })
            return {"decision": "AUTO", "reconciliation_id": status["id"], "reason": "Recovered via postcondition verifier"}
        return None

    def evaluate_escalation_tier(self, scratchpad: WorkingMemoryScratchpad) -> str:
        if scratchpad.ambiguity_flag or scratchpad.stale_data_flag or scratchpad.cross_period_flag or scratchpad.flags.get("ambiguity") or scratchpad.flags.get("stale") or scratchpad.flags.get("cross_period"):
            return "REVIEW"
        if scratchpad.cross_currency_flag or scratchpad.flags.get("fx_mismatch"):
            return "BLOCK"
        return "AUTO"

    def get_runbook(self, runbook_name: str) -> Optional[Dict[str, Any]]:
        return self.runbooks.get(runbook_name)


# -----------------------------------------------------------------------------
# Unified Cognitive Memory Coordinator
# -----------------------------------------------------------------------------

class CognitiveMemorySystem:
    def __init__(self, db_path: Optional[str] = None, memory_file: Optional[str] = None):
        self.episodic = EpisodicMemoryStore()
        self.semantic = SemanticMemoryStore(memory_file=memory_file) if memory_file else SemanticMemoryStore()
        self.procedural = ProceduralMemoryStore()

    def create_working_memory(self, bank_txn_id: str) -> WorkingMemoryScratchpad:
        return WorkingMemoryScratchpad(bank_transaction_id=bank_txn_id)


# Class Alias
CognitiveMemoryEngine = CognitiveMemorySystem
