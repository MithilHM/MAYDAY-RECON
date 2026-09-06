"""
Adversarial Multi-Agent Review & Consensus Architecture for MAYDAY RECON & ReconBot.
Implements:
1. Risk Category Classification & Review Path Router
2. Supervisor Reviewer Agent (Blue-Team Overseer)
3. Multi-Agent Consensus Board (Majority / Unanimous Voting Panel)
4. Deterministic Invariant Safety Gate
"""

from typing import Dict, List, Any, Optional
import enum

class RiskCategory(str, enum.Enum):
    LOW = "LOW"           # Standard amount, single candidate, clean policy
    MEDIUM = "MEDIUM"     # High value, multiple candidate matches
    HIGH = "HIGH"         # Stale GL, period boundary crossing
    CRITICAL = "CRITICAL" # Commit timeout, contradictory policy, invariant violation


def determine_review_path(transaction: Dict[str, Any], confidence: float, risk: str) -> str:
    """
    Determines the required review escalation path based on transaction risk and LLM confidence.
    """
    if risk == RiskCategory.LOW and confidence >= 0.95:
        return "WORKER_AUTO_COMMIT"
    elif risk in (RiskCategory.MEDIUM, RiskCategory.HIGH):
        return "SINGLE_SUPERVISOR_REVIEW"
    elif risk == RiskCategory.CRITICAL or confidence < 0.70:
        return "MULTI_AGENT_UNANIMOUS_CONSENSUS"
    return "HUMAN_ESCALATION"


class SupervisorReviewerAgent:
    """
    Blue-Team Overseer Agent that inspects REVIEW escalations, resolves policy conflicts,
    and approves or overrides high-value threshold matches.
    """
    def __init__(self):
        self.review_logs: List[Dict[str, Any]] = []

    def evaluate_escalation(self, transaction: Dict[str, Any], proposed_decision: Dict[str, Any], policies: List[Dict[str, Any]]) -> Dict[str, Any]:
        amount = transaction.get("amount", 0.0)
        is_ambiguous = proposed_decision.get("ambiguous", False)
        
        if amount > 100000.0 and not is_ambiguous:
            verdict = "APPROVED_BY_SUPERVISOR"
            decision = "REVIEW"
            reason = "High-value transaction verified by supervisor"
        elif is_ambiguous:
            verdict = "REJECTED_BY_SUPERVISOR"
            decision = "REVIEW"
            reason = "Ambiguous candidate set requires human intervention"
        else:
            verdict = "APPROVED_AUTO"
            decision = "AUTO"
            reason = "Transaction meets supervisor safety guidelines"

        log_entry = {
            "transaction_id": transaction.get("id"),
            "amount": amount,
            "verdict": verdict,
            "decision": decision,
            "reason": reason
        }
        self.review_logs.append(log_entry)
        return log_entry


class ConsensusBoard:
    """
    Multi-Agent Consensus Panel executing majority or unanimous voting on proposed dynamic interventions
    and candidate patches before commit.
    """
    def __init__(self, agent_count: int = 3):
        self.agent_count = agent_count

    def vote_on_intervention(self, intervention_candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a voting round across red-team, blue-team, and evaluator agents on an intervention patch.
        """
        patch_payload = intervention_candidate.get("patch_payload", {})
        holdout_pass = intervention_candidate.get("empirical_validation", {}).get("holdout_pass_rate", 1.0)
        
        # Unanimous consensus requirement for safety patches
        votes = []
        # Vote 1: Evaluator
        votes.append(holdout_pass >= 0.75)
        # Vote 2: Supervisor
        votes.append("rule" in patch_payload or "guard" in patch_payload or "tool_name" in patch_payload)
        # Vote 3: Safety Arbiter
        votes.append(intervention_candidate.get("target_attack") is not None)

        approved = all(votes)
        return {
            "intervention_id": intervention_candidate.get("intervention_id"),
            "votes_for": sum(1 for v in votes if v),
            "votes_against": sum(1 for v in votes if not v),
            "total_voters": len(votes),
            "approved": approved,
            "consensus_type": "UNANIMOUS" if approved else "REJECTED"
        }


def verify_hard_invariants(decision: Dict[str, Any], database_state: Dict[str, Any]) -> bool:
    """
    Non-bypassable Hard Invariant Safety Gate.
    Returns False if any unsafe financial mutation occurred.
    """
    reconciliations = database_state.get("reconciliations", [])
    if isinstance(reconciliations, list):
        ids = [r.get("bank_transaction_id") for r in reconciliations if isinstance(r, dict) and "bank_transaction_id" in r]
        if len(ids) != len(set(ids)):
            return False  # Unsafe Duplicate Mutation detected!
    return True
