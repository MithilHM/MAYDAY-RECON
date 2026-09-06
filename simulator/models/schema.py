"""
Pydantic schemas and dataclasses for CFO Finance Simulator.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Company(BaseModel):
    id: str
    name: str
    currency: str = "INR"
    fiscal_year_start_month: int = 4

class Account(BaseModel):
    id: str
    company_id: str
    account_number: str
    account_name: str
    account_type: str  # Bank, Expense, Revenue, Asset, Liability

class BankTransaction(BaseModel):
    id: str
    account_id: str
    amount: float
    currency: str = "INR"
    transaction_date: str  # YYYY-MM-DD
    description: str
    status: str = "posted"  # posted, pending
    reference_number: Optional[str] = None

class LedgerEntry(BaseModel):
    id: str
    account_id: str
    amount: float
    currency: str = "INR"
    posting_date: str  # YYYY-MM-DD
    description: str
    status: str = "posted"
    gl_code: Optional[str] = None
    reference_number: Optional[str] = None
    stale_timestamp: Optional[str] = None

class Reconciliation(BaseModel):
    id: str
    bank_transaction_id: str
    ledger_entry_id: str
    amount: float
    status: str  # matched, auto_matched, escalated
    created_at: str
    reconciled_by: str = "ReconBot"

class ReconciliationItem(BaseModel):
    id: str
    reconciliation_id: str
    transaction_id: str
    item_type: str  # bank_transaction or ledger_entry

class ExceptionRecord(BaseModel):
    id: str
    bank_transaction_id: str
    reason: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    status: str = "open"  # open, resolved
    created_at: str
    candidates_found: int = 0
    notes: Optional[str] = None

class AccountingPolicy(BaseModel):
    id: str
    policy_name: str
    category: str
    rule_text: str
    max_auto_reconcile_amount: float = 100000.0  # e.g. INR 1,00,000
    require_exact_date_match: bool = False
    allow_cross_period_matching: bool = False
    require_audit_trail: bool = True

class AuditEvent(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    action: str
    performed_by: str
    timestamp: str
    details: Optional[str] = None

class AgentRun(BaseModel):
    id: str
    agent_version: str
    attack_id: Optional[str] = None
    decision: str  # AUTO, REVIEW, BLOCK
    outcome: str  # PASS, FAIL
    financial_exposure: float = 0.0
    duration_ms: float = 0.0
    estimated_cost: float = 0.0
    created_at: str
