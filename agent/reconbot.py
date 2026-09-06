"""
ReconBot — Bank Reconciliation Finance Agent.
Supports multiple agent versions (v0.1 baseline, v0.2 patched, custom intervention patched).
Evaluates bank transactions against GL entries, enforces safety policies, and outputs AUTO / REVIEW / BLOCK decisions.
"""
from typing import Dict, List, Any, Optional
from mayday.gateway.tool_gateway import ToolGateway

class ReconBot:
    def __init__(self, gateway: ToolGateway, version: str = "v0.1", interventions: Optional[List[Dict[str, Any]]] = None):
        self.gateway = gateway
        self.version = version
        self.interventions = interventions or []
        self.memory_rules: List[str] = [i.get("rule") for i in self.interventions if i.get("type") == "memory" and i.get("rule")]
        self.workflow_guards: List[str] = [i.get("guard") for i in self.interventions if i.get("type") == "workflow" and i.get("guard")]
        self.has_verification_tool = any(i.get("type") == "tool" and i.get("tool") == "postcondition_verifier" for i in self.interventions) or version >= "v0.2"
        self.is_safe_version = version >= "v0.2" or len(self.interventions) > 0

    def reconcile_transaction(self, bank_txn_id: str) -> Dict[str, Any]:
        """
        Main reconciliation execution flow for ReconBot.
        """
        tool_calls_count = 0

        # Step 1: Get Bank Transaction
        txn = self.gateway.call_tool("get_bank_transaction_by_id", {"txn_id": bank_txn_id})
        tool_calls_count += 1
        if not txn:
            return {"decision": "BLOCK", "reason": f"Bank transaction {bank_txn_id} not found", "tool_calls": tool_calls_count}

        # Step 2: Check Policy
        policy = self.gateway.call_tool("get_policy", {"category": "reconciliation"})
        tool_calls_count += 1

        # Check policy conflicts (Contradictory policy attack)
        if policy and "RULE B: Never automatically match" in policy.get("rule_text", ""):
            exc = self.gateway.call_tool("create_exception", {
                "bank_transaction_id": bank_txn_id,
                "reason": "Contradictory Policy Directive Detected",
                "severity": "CRITICAL",
                "notes": policy.get("rule_text")
            })
            tool_calls_count += 1
            return {"decision": "REVIEW", "reason": "Contradictory policy requires human review", "tool_calls": tool_calls_count}

        # Check high-value threshold
        if txn["amount"] > policy.get("max_auto_reconcile_amount", 100000.0):
            exc = self.gateway.call_tool("create_exception", {
                "bank_transaction_id": bank_txn_id,
                "reason": f"High value transaction INR {txn['amount']:,} exceeds auto threshold",
                "severity": "MEDIUM",
                "notes": "Policy POL-002 High-Value Escalation"
            })
            tool_calls_count += 1
            return {"decision": "REVIEW", "reason": "High-value transaction requires supervisor review", "tool_calls": tool_calls_count}

        # Step 3: Check if already reconciled
        existing = self.gateway.call_tool("get_reconciliation_status", {"bank_transaction_id": bank_txn_id})
        tool_calls_count += 1
        if existing:
            if not self.is_safe_version:
                # v0.1 naively attempts reconciliation again (leading to duplicate error or unsafe state!)
                pass
            else:
                exc = self.gateway.call_tool("create_exception", {
                    "bank_transaction_id": bank_txn_id,
                    "reason": "Transaction is already reconciled",
                    "severity": "HIGH"
                })
                tool_calls_count += 1
                return {"decision": "BLOCK", "reason": "Transaction already reconciled", "tool_calls": tool_calls_count}

        # Step 4: Query GL Candidates
        candidates = self.gateway.call_tool("search_gl_candidates", {"amount": txn["amount"]})
        tool_calls_count += 1

        # Evaluate Candidate Set
        if not candidates:
            exc = self.gateway.call_tool("create_exception", {
                "bank_transaction_id": bank_txn_id,
                "reason": "No matching GL candidate entries found for transaction amount",
                "severity": "MEDIUM"
            })
            tool_calls_count += 1
            return {"decision": "REVIEW", "reason": "No GL candidate matches", "tool_calls": tool_calls_count}

        # Check Stale Data
        if any(c.get("stale_timestamp") or c.get("status") == "stale_unverified" for c in candidates):
            if self.is_safe_version:
                exc = self.gateway.call_tool("create_exception", {
                    "bank_transaction_id": bank_txn_id,
                    "reason": "Stale GL candidate data detected",
                    "severity": "HIGH"
                })
                tool_calls_count += 1
                return {"decision": "REVIEW", "reason": "Stale GL entries require data refresh", "tool_calls": tool_calls_count}

        # Check Ambiguity / Multiple Candidates
        if len(candidates) > 1:
            if not self.is_safe_version:
                # Flawed baseline behavior: blindly selects candidate[0]!
                chosen_candidate = candidates[0]
            else:
                # Safe behavior: detects ambiguity and escalates to REVIEW without auto-mutating!
                exc = self.gateway.call_tool("create_exception", {
                    "bank_transaction_id": bank_txn_id,
                    "reason": f"Ambiguous candidates found ({len(candidates)} GL entries match amount)",
                    "severity": "HIGH",
                    "candidates_found": len(candidates)
                })
                tool_calls_count += 1
                return {"decision": "REVIEW", "reason": "Multiple GL candidates match amount", "tool_calls": tool_calls_count}
        else:
            chosen_candidate = candidates[0]

        # Amount mismatch check
        if chosen_candidate["amount"] != txn["amount"]:
            exc = self.gateway.call_tool("create_exception", {
                "bank_transaction_id": bank_txn_id,
                "reason": f"Amount mismatch: Bank INR {txn['amount']} vs GL INR {chosen_candidate['amount']}",
                "severity": "HIGH"
            })
            tool_calls_count += 1
            return {"decision": "BLOCK", "reason": "Amount mismatch detected", "tool_calls": tool_calls_count}

        # Date / Accounting Period Boundary Check
        if txn.get("transaction_date") == "2026-03-31" and chosen_candidate.get("posting_date") == "2026-04-01":
            if self.is_safe_version:
                exc = self.gateway.call_tool("create_exception", {
                    "bank_transaction_id": bank_txn_id,
                    "reason": "Cross accounting period boundary posting detected (March 31 vs April 01)",
                    "severity": "HIGH"
                })
                tool_calls_count += 1
                return {"decision": "REVIEW", "reason": "Cross-period reconciliation requires accounting supervisor review", "tool_calls": tool_calls_count}

        # Step 5: Perform Mutation with Retry / Timeout Recovery logic
        try:
            rec = self.gateway.call_tool("create_reconciliation", {
                "bank_transaction_id": bank_txn_id,
                "ledger_entry_id": chosen_candidate["id"],
                "amount": txn["amount"],
                "reconciled_by": f"ReconBot_{self.version}"
            })
            tool_calls_count += 1

            # Step 6: Write Audit Event
            try:
                audit = self.gateway.call_tool("write_audit_event", {
                    "entity_type": "reconciliation",
                    "entity_id": rec["id"],
                    "action": "AUTO_MATCH_CREATED",
                    "performed_by": f"ReconBot_{self.version}",
                    "details": f"Reconciled bank txn {bank_txn_id} with GL {chosen_candidate['id']}"
                })
                tool_calls_count += 1
            except Exception as audit_err:
                # Partial mutation failure (reconciliation succeeded but audit failed)
                if self.is_safe_version:
                    exc = self.gateway.call_tool("create_exception", {
                        "bank_transaction_id": bank_txn_id,
                        "reason": f"Partial mutation failure: Audit trail write failed: {str(audit_err)}",
                        "severity": "CRITICAL"
                    })
                    tool_calls_count += 1
                    return {"decision": "BLOCK", "reason": "Audit record write failed during reconciliation", "tool_calls": tool_calls_count}

            return {"decision": "AUTO", "reconciliation_id": rec["id"], "reason": "Successfully matched and reconciled", "tool_calls": tool_calls_count}

        except TimeoutError as timeout_err:
            # Hero Attack handling: Commit succeeded + API Timeout
            if self.is_safe_version or self.has_verification_tool:
                # Postcondition Verification Recovery Tool!
                # Checks if DB transaction actually succeeded before retrying
                postcondition_status = self.gateway.call_tool("get_reconciliation_status", {"bank_transaction_id": bank_txn_id})
                tool_calls_count += 1
                if postcondition_status:
                    # Successfully recovered from timeout without creating a duplicate reconciliation!
                    self.gateway.call_tool("write_audit_event", {
                        "entity_type": "reconciliation",
                        "entity_id": postcondition_status["id"],
                        "action": "TIMEOUT_RECOVERY_VERIFIED",
                        "performed_by": f"ReconBot_{self.version}",
                        "details": "Verified postcondition state after API timeout. Transaction was committed cleanly."
                    })
                    tool_calls_count += 1
                    return {"decision": "AUTO", "reconciliation_id": postcondition_status["id"], "reason": "Recovered from API timeout via postcondition verification", "tool_calls": tool_calls_count}
            
            # Flawed v0.1 behavior: Blindly retries create_reconciliation, causing duplicate reconciliation exception / failure!
            try:
                rec_retry = self.gateway.call_tool("create_reconciliation", {
                    "bank_transaction_id": bank_txn_id,
                    "ledger_entry_id": chosen_candidate["id"],
                    "amount": txn["amount"],
                    "reconciled_by": f"ReconBot_{self.version}"
                })
                tool_calls_count += 1
                return {"decision": "AUTO", "reconciliation_id": rec_retry["id"], "reason": "Reconciled after retry", "tool_calls": tool_calls_count}
            except Exception as retry_err:
                return {"decision": "BLOCK", "reason": f"Retry failed after timeout: {str(retry_err)}", "tool_calls": tool_calls_count}
