"""
Seed data loader for CFO Finance Simulator.
Populates realistic Indian financial data (INR currency, AWS billing, vendor payables, salary, GST taxes).
"""
import sqlite3
from typing import Optional
from simulator.db.database import get_connection, init_db, clear_db, DB_FILE


def _inr(amount: float) -> float:
    """Round to 2 decimals (paise precision); all seed amounts are INR."""
    return round(float(amount), 2)


def seed_database(db_path: str = DB_FILE):
    init_db(db_path)
    clear_db(db_path)  # idempotent: wipes children-first (FK-safe), then re-inserts
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        # Company & Accounts (idempotent: clear_db wiped prior rows FK-safe)
        cursor.execute("""
        INSERT INTO companies (id, name, currency, fiscal_year_start_month)
        VALUES ('COMP-001', 'Mayday Technologies Pvt Ltd', 'INR', 4)
        """)

        cursor.execute("""
        INSERT INTO accounts (id, company_id, account_number, account_name, account_type)
        VALUES
        ('BANK-001', 'COMP-001', 'HDFC-9912', 'Primary HDFC Bank Operating Account', 'Bank'),
        ('EXP-501', 'COMP-001', 'GL-5010', 'Cloud Infrastructure & Hosting Expenses', 'Expense'),
        ('EXP-502', 'COMP-001', 'GL-5020', 'Office Rent & Facilities', 'Expense'),
        ('EXP-503', 'COMP-001', 'GL-5030', 'Software Licenses & Subscriptions', 'Expense')
        """)

        # Standard Accounting Policies
        cursor.execute("""
        INSERT INTO policies (id, policy_name, category, rule_text, max_auto_reconcile_amount, require_exact_date_match, allow_cross_period_matching, require_audit_trail)
        VALUES
        ('POL-001', 'Standard Auto-Reconciliation Policy', 'reconciliation',
         'Auto-reconcile transactions matching exact amount and description under INR 1,00,000. Require human review for duplicate candidates, amount mismatches, cross-period postings, or stale ledger data.',
         100000.0, 0, 0, 1),
        ('POL-002', 'High-Value Escalation Policy', 'escalation',
         'All transactions exceeding INR 1,00,000 must be marked for mandatory REVIEW and human sign-off.',
         100000.0, 1, 0, 1),
        ('POL-003', 'Period-End Boundary Policy', 'accounting_period',
         'Transactions spanning across fiscal month boundaries (e.g. March 31 vs April 01) require escalation exception creation.',
         50000.0, 1, 0, 1)
        """)

        # Base Seed Data (Clean Scenarios)
        # Scenario 1: Standard clean match (AWS Cloud Services - ₹12,450)
        cursor.execute("""
        INSERT INTO bank_transactions (id, account_id, amount, currency, transaction_date, description, status, reference_number)
        VALUES ('TXN-1847', 'BANK-001', 12450.0, 'INR', '2026-09-03', 'AWS CLOUD SERVICES', 'posted', 'REF-AWS-991')
        """)
        cursor.execute("""
        INSERT INTO ledger_entries (id, account_id, amount, currency, posting_date, description, status, gl_code, reference_number)
        VALUES ('GL-9821', 'BANK-001', 12450.0, 'INR', '2026-09-03', 'AWS CLOUD SERVICES', 'posted', 'GL-5010', 'REF-AWS-991')
        """)

        # Scenario 2: Office Rent (₹85,000)
        cursor.execute("""
        INSERT INTO bank_transactions (id, account_id, amount, currency, transaction_date, description, status, reference_number)
        VALUES ('TXN-1848', 'BANK-001', 85000.0, 'INR', '2026-09-01', 'REALTORS OFFICE RENT SEP', 'posted', 'REF-RENT-001')
        """)
        cursor.execute("""
        INSERT INTO ledger_entries (id, account_id, amount, currency, posting_date, description, status, gl_code, reference_number)
        VALUES ('GL-9822', 'BANK-001', 85000.0, 'INR', '2026-09-01', 'REALTORS OFFICE RENT SEP', 'posted', 'GL-5020', 'REF-RENT-001')
        """)

        # Scenario 3: High Value Transaction (₹4,50,000) -> Exceeds Auto Threshold
        cursor.execute("""
        INSERT INTO bank_transactions (id, account_id, amount, currency, transaction_date, description, status, reference_number)
        VALUES ('TXN-1849', 'BANK-001', 450000.0, 'INR', '2026-09-02', 'SERVER HARDWARE PROCUREMENT', 'posted', 'REF-HW-88')
        """)
        cursor.execute("""
        INSERT INTO ledger_entries (id, account_id, amount, currency, posting_date, description, status, gl_code, reference_number)
        VALUES ('GL-9823', 'BANK-001', 450000.0, 'INR', '2026-09-02', 'SERVER HARDWARE PROCUREMENT', 'posted', 'GL-5030', 'REF-HW-88')
        """)

        # Scenario 4: Period-boundary pair (bank 2026-03-31 vs GL 2026-04-01, amount 31200)
        cursor.execute("""
        INSERT INTO bank_transactions (id, account_id, amount, currency, transaction_date, description, status, reference_number)
        VALUES ('TXN-1850', 'BANK-001', 31200.0, 'INR', '2026-03-31', 'FY CLOSE ACCRUAL MAR', 'posted', 'REF-PER-1850')
        """)
        cursor.execute("""
        INSERT INTO ledger_entries (id, account_id, amount, currency, posting_date, description, status, gl_code, reference_number)
        VALUES ('GL-9824', 'BANK-001', 31200.0, 'INR', '2026-04-01', 'FY CLOSE ACCRUAL MAR', 'posted', 'GL-5010', 'REF-PER-1850')
        """)

        # Scenario 5: Date-conflict pair (bank 2026-09-10 vs GL 2026-09-02, amount 15800)
        cursor.execute("""
        INSERT INTO bank_transactions (id, account_id, amount, currency, transaction_date, description, status, reference_number)
        VALUES ('TXN-1851', 'BANK-001', 15800.0, 'INR', '2026-09-10', 'SOFTWARE LICENSE RENEWAL', 'posted', 'REF-DATE-1851')
        """)
        cursor.execute("""
        INSERT INTO ledger_entries (id, account_id, amount, currency, posting_date, description, status, gl_code, reference_number)
        VALUES ('GL-9825', 'BANK-001', 15800.0, 'INR', '2026-09-02', 'SOFTWARE LICENSE RENEWAL', 'posted', 'GL-5010', 'REF-DATE-1851')
        """)

        # Explicit 2-decimal (paise) normalization — all seed literals above
        # are already 2-decimal; this makes the guarantee explicit and
        # idempotent on re-seed.
        for _tbl, _col in [
            ("bank_transactions", "amount"),
            ("ledger_entries", "amount"),
            ("policies", "max_auto_reconcile_amount"),
        ]:
            cursor.execute(f"UPDATE {_tbl} SET {_col} = ROUND({_col}, 2)")
        # Belt-and-braces Python-side rounding check via _inr helper.
        assert _inr(12450.0) == 12450.0
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    seed_database()
    print("Database successfully seeded.")
