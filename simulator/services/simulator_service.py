"""
CFO Simulator Services module.
Provides deterministic financial operations and mutations.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from simulator.db.database import get_connection, DB_FILE

class CFOSimulatorService:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path

    def get_bank_transactions(self, account_id: str = "BANK-001", status: Optional[str] = "posted") -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM bank_transactions WHERE account_id = ? AND status = ?", (account_id, status))
        else:
            cursor.execute("SELECT * FROM bank_transactions WHERE account_id = ?", (account_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_bank_transaction_by_id(self, txn_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bank_transactions WHERE id = ?", (txn_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_gl_entries(self, account_id: str = "BANK-001") -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ledger_entries WHERE account_id = ?", (account_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def search_gl_candidates(self, amount: float, description_keyword: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ledger_entries WHERE amount = ?", (amount,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_reconciliation_status(self, bank_transaction_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reconciliations WHERE bank_transaction_id = ?", (bank_transaction_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_policy(self, category: str = "reconciliation") -> Optional[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM policies WHERE category = ?", (category,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_reconciliation(self, bank_transaction_id: str, ledger_entry_id: str, amount: float, reconciled_by: str = "ReconBot") -> Dict[str, Any]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        
        # Check if already reconciled
        cursor.execute("SELECT * FROM reconciliations WHERE bank_transaction_id = ?", (bank_transaction_id,))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            raise ValueError(f"Transaction {bank_transaction_id} is already reconciled!")

        rec_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
        created_at = datetime.now().isoformat()
        
        cursor.execute("""
        INSERT INTO reconciliations (id, bank_transaction_id, ledger_entry_id, amount, status, created_at, reconciled_by)
        VALUES (?, ?, ?, ?, 'matched', ?, ?)
        """, (rec_id, bank_transaction_id, ledger_entry_id, amount, created_at, reconciled_by))

        cursor.execute("""
        INSERT INTO reconciliation_items (id, reconciliation_id, transaction_id, item_type)
        VALUES (?, ?, ?, 'bank_transaction'), (?, ?, ?, 'ledger_entry')
        """, (f"ITEM-1-{rec_id}", rec_id, bank_transaction_id, f"ITEM-2-{rec_id}", rec_id, ledger_entry_id))

        conn.commit()
        conn.close()
        return {"id": rec_id, "bank_transaction_id": bank_transaction_id, "ledger_entry_id": ledger_entry_id, "status": "matched"}

    def create_exception(self, bank_transaction_id: str, reason: str, severity: str = "HIGH", candidates_found: int = 0, notes: Optional[str] = None) -> Dict[str, Any]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        exc_id = f"EXC-{uuid.uuid4().hex[:8].upper()}"
        created_at = datetime.now().isoformat()

        cursor.execute("""
        INSERT INTO exceptions (id, bank_transaction_id, reason, severity, status, created_at, candidates_found, notes)
        VALUES (?, ?, ?, ?, 'open', ?, ?, ?)
        """, (exc_id, bank_transaction_id, reason, severity, created_at, candidates_found, notes or ""))

        conn.commit()
        conn.close()
        return {"id": exc_id, "bank_transaction_id": bank_transaction_id, "reason": reason, "severity": severity}

    def write_audit_event(self, entity_type: str, entity_id: str, action: str, performed_by: str = "ReconBot", details: Optional[str] = None) -> Dict[str, Any]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.now().isoformat()

        cursor.execute("""
        INSERT INTO audit_events (id, entity_type, entity_id, action, performed_by, timestamp, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (audit_id, entity_type, entity_id, action, performed_by, timestamp, details or ""))

        conn.commit()
        conn.close()
        return {"id": audit_id, "entity_type": entity_type, "entity_id": entity_id, "action": action}
