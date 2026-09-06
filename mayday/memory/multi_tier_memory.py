"""
Multi-Tier Cognitive Memory System for MAYDAY RECON & ReconBot.
Implements:
1. Working Memory (Scratchpad / In-Flight Context & Tool Call Budget)
2. Episodic Memory (Trace Records, Environment Snapshots, Tool Invocations)
3. Semantic Memory (Policy Rules, Accounting Standards, Vulnerability Taxonomy)
4. Procedural Memory (Runbooks, Postcondition Verification, Decision Rules)
"""
import json
import os
import time
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# 1. Working Memory (In-Flight Scratchpad Context)
# -----------------------------------------------------------------------------

class WorkingMemoryScratchpad(BaseModel):
    bank_transaction_id: str
    current_transaction: Optional[Dict[str, Any]] = None
    retrieved_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    ambiguity_flag: bool = False
    stale_data_flag: bool = False
    cross_period_flag: bool = False
    cross_currency_flag: bool = False
    pending_exceptions: List[Dict[str, Any]] = Field(default_factory=list)
    tool_calls_count: int = 0
    in_flight_mutation: Optional[Dict[str, Any]] = None
    thought_history: List[str] = Field(default_factory=list)

    def record_thought(self, thought: str):
        self.thought_history.append(f"[{time.strftime('%H:%M:%S')}] {thought}")

# -----------------------------------------------------------------------------
# 2. Episodic Memory (Temporal Execution Traces & Snapshots)
# -----------------------------------------------------------------------------

class EpisodicMemoryStore:
    def __init__(self, trace_dir: str = os.path.join(os.path.dirname(__file__), "traces")):
        self.trace_dir = trace_dir
        os.makedirs(self.trace_dir, exist_ok=True)
        self.traces: List[Dict[str, Any]] = []

    def record_episode(self, trace_record: Dict[str, Any]):
        self.traces.append(trace_record)
        # Save to episodic file
        trace_file = os.path.join(self.trace_dir, f"{trace_record.get('run_id', 'episode')}.json")
        try:
            with open(trace_file, "w") as f:
                json.dump(trace_record, f, indent=2)
        except Exception:
            pass

    def get_episode_by_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        for tr in self.traces:
            if tr.get("run_id") == run_id:
                return tr
        return None

# -----------------------------------------------------------------------------
# 3. Semantic Memory (Policy Rules & Vulnerability Index)
# -----------------------------------------------------------------------------

class SemanticMemoryStore:
    def __init__(self):
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

class ProceduralMemoryStore:
    def __init__(self):
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

    def get_runbook(self, runbook_name: str) -> Optional[Dict[str, Any]]:
        return self.runbooks.get(runbook_name)

# -----------------------------------------------------------------------------
# Unified Cognitive Memory Coordinator
# -----------------------------------------------------------------------------

class CognitiveMemorySystem:
    def __init__(self):
        self.episodic = EpisodicMemoryStore()
        self.semantic = SemanticMemoryStore()
        self.procedural = ProceduralMemoryStore()

    def create_working_memory(self, bank_txn_id: str) -> WorkingMemoryScratchpad:
        return WorkingMemoryScratchpad(bank_transaction_id=bank_txn_id)
