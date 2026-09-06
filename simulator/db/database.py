"""
SQLite database engine for the CFO Finance Simulator.
Supports deterministic initialization, seed data loading, state reset, and snapshot comparison.
"""
import sqlite3
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "cfo_simulator.db")

def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Harden: enforce FK constraints on every connection.
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db(db_path: str = DB_FILE):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS companies (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        currency TEXT NOT NULL,
        fiscal_year_start_month INTEGER DEFAULT 4
    );

    CREATE TABLE IF NOT EXISTS accounts (
        id TEXT PRIMARY KEY,
        company_id TEXT NOT NULL REFERENCES companies(id),
        account_number TEXT NOT NULL,
        account_name TEXT NOT NULL,
        account_type TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS bank_transactions (
        id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL REFERENCES accounts(id),
        amount REAL NOT NULL CHECK(amount >= 0),
        currency TEXT NOT NULL,
        transaction_date TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'posted',
        reference_number TEXT
    );

    CREATE TABLE IF NOT EXISTS ledger_entries (
        id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL REFERENCES accounts(id),
        amount REAL NOT NULL CHECK(amount >= 0),
        currency TEXT NOT NULL,
        posting_date TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'posted',
        gl_code TEXT,
        reference_number TEXT,
        stale_timestamp TEXT
    );

    CREATE TABLE IF NOT EXISTS reconciliations (
        id TEXT PRIMARY KEY,
        bank_transaction_id TEXT NOT NULL REFERENCES bank_transactions(id),
        ledger_entry_id TEXT NOT NULL REFERENCES ledger_entries(id),
        amount REAL NOT NULL CHECK(amount >= 0),
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        reconciled_by TEXT DEFAULT 'ReconBot'
    );

    CREATE TABLE IF NOT EXISTS reconciliation_items (
        id TEXT PRIMARY KEY,
        reconciliation_id TEXT NOT NULL REFERENCES reconciliations(id),
        transaction_id TEXT NOT NULL,
        item_type TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS exceptions (
        id TEXT PRIMARY KEY,
        bank_transaction_id TEXT NOT NULL REFERENCES bank_transactions(id),
        reason TEXT NOT NULL,
        severity TEXT NOT NULL,
        status TEXT DEFAULT 'open',
        created_at TEXT NOT NULL,
        candidates_found INTEGER DEFAULT 0,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS policies (
        id TEXT PRIMARY KEY,
        policy_name TEXT NOT NULL,
        category TEXT NOT NULL,
        rule_text TEXT NOT NULL,
        max_auto_reconcile_amount REAL DEFAULT 100000.0 CHECK(max_auto_reconcile_amount >= 0),
        require_exact_date_match INTEGER DEFAULT 0,
        allow_cross_period_matching INTEGER DEFAULT 0,
        require_audit_trail INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS audit_events (
        id TEXT PRIMARY KEY,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        action TEXT NOT NULL,
        performed_by TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        details TEXT
    );

    CREATE TABLE IF NOT EXISTS agent_runs (
        id TEXT PRIMARY KEY,
        agent_version TEXT NOT NULL,
        attack_id TEXT,
        decision TEXT NOT NULL,
        outcome TEXT NOT NULL,
        financial_exposure REAL DEFAULT 0.0 CHECK(financial_exposure >= 0),
        duration_ms REAL DEFAULT 0.0 CHECK(duration_ms >= 0),
        estimated_cost REAL DEFAULT 0.0 CHECK(estimated_cost >= 0),
        created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_ledger_amount ON ledger_entries(amount);
    CREATE INDEX IF NOT EXISTS idx_rec_txn ON reconciliations(bank_transaction_id);
    CREATE INDEX IF NOT EXISTS idx_bank_acct ON bank_transactions(account_id);
    """)

    conn.commit()
    conn.close()

def clear_db(db_path: str = DB_FILE):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    # FK-safe order: children before parents.
    tables = [
        "reconciliation_items", "reconciliations", "exceptions",
        "audit_events", "agent_runs", "bank_transactions",
        "ledger_entries", "accounts", "policies", "companies"
    ]
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()

# Lightweight snapshot tables (fast path when full=False).
_LIGHT_SNAPSHOT_TABLES = ["reconciliations", "exceptions", "audit_events"]

def dump_state(db_path: str = DB_FILE, full: bool = True, tables: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Capture database snapshot for deterministic evaluation.

    Args:
        db_path: SQLite file path.
        full: when True (default, backwards compatible) dump all tables.
            When False, dump a lightweight subset (reconciliations,
            exceptions, audit_events) unless `tables` overrides it.
        tables: explicit table allow-list; validated against known tables.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    all_tables = [
        "companies", "accounts", "bank_transactions", "ledger_entries",
        "reconciliations", "reconciliation_items", "exceptions",
        "policies", "audit_events", "agent_runs"
    ]
    if tables is not None:
        unknown = [t for t in tables if t not in all_tables]
        if unknown:
            conn.close()
            raise ValueError(f"Unknown tables in dump_state: {unknown}")
        selected = list(tables)
    elif full:
        selected = all_tables
    else:
        selected = list(_LIGHT_SNAPSHOT_TABLES)
    snapshot = {}
    try:
        for table in selected:
            cursor.execute(f"SELECT * FROM {table}")
            rows = [dict(r) for r in cursor.fetchall()]
            snapshot[table] = rows
    finally:
        conn.close()
    return snapshot
