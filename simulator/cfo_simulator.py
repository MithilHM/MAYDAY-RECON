"""
MAYDAY RECON - CFO Simulator Implementation

The CFO Simulator simulates banking data and reconciliation scenarios
that attackers might target. It provides:
1. Realistic transaction data generation
2. Bank statement data generation
3. Ledger data generation
4. Scenario-based reconciliation flows
"""

import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import hashlib
from dataclasses import dataclass
import json


@dataclass
class Transaction:
    """Represents a financial transaction"""
    tx_id: str
    amount: float
    timestamp: datetime
    description: str
    account_from: str
    account_to: str
    status: str  # pending, completed, failed, disputed

    @property
    def account_id(self) -> str:
        return self.account_from

    def to_dict(self) -> Dict:
        return {
            "tx_id": self.tx_id,
            "amount": round(self.amount, 2),
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "account_from": self.account_from,
            "account_to": self.account_to,
            "status": self.status
        }


@dataclass
class BankStatement:
    """Represents a bank statement for reconciliation"""
    statement_id: str
    bank_name: str
    start_date: datetime
    end_date: datetime
    total_debits: float
    total_credits: float
    closing_balance: float
    transactions: List[Transaction]

    def calculate_balance(self) -> float:
        """Calculate running balance"""
        balance = 0.0
        for tx in self.transactions:
            if tx.status == "completed":
                if tx.account_from == "system":
                    balance -= tx.amount
                elif tx.account_to == "system":
                    balance += tx.amount
        return balance

    def to_dict(self) -> Dict:
        return {
            "statement_id": self.statement_id,
            "bank_name": self.bank_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_debits": round(self.total_debits, 2),
            "total_credits": round(self.total_credits, 2),
            "closing_balance": round(self.closing_balance, 2),
            "transactions_count": len(self.transactions)
        }


@dataclass
class LedgerEntry:
    """Represents a ledger entry"""
    entry_id: str
    tx_id: str
    amount: float
    debit_credit: str  # DEBIT, CREDIT
    account: str
    transaction_date: datetime
    posted_date: datetime

    def to_dict(self) -> Dict:
        return {
            "entry_id": self.entry_id,
            "tx_id": self.tx_id,
            "amount": round(self.amount, 2),
            "debit_credit": self.debit_credit,
            "account": self.account,
            "transaction_date": self.transaction_date.isoformat(),
            "posted_date": self.posted_date.isoformat()
        }


class CFOSimulator:
    """
    Simulates CFO-level reconciliation scenarios
    Generates realistic financial data for attack testing
    """

    def __init__(self, bank_name: str = "SimBank"):
        self.bank_name = bank_name
        self.transaction_types = [
            "Wire Transfer", "ACH Transaction", "Check Payment",
            "Electronic Deposit", "Bank Draft", "Overdraft Protection",
            "Fee Charge", "Interest Credit", "Tax Payment", "Loan Payment"
        ]
        self.accounts = [
            "Primary Operating Account",
            "Secondary Business Account",
            "Treasury Account",
            "Suspense Account",
            "ESPP Account"
        ]

    def generate_transactions(
        self,
        count: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[Transaction]:
        """
        Generate realistic transaction data
        """
        if "transaction_count" in kwargs:
            count = kwargs["transaction_count"]
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)

        if end_date is None:
            end_date = datetime.now()

        transactions = []

        for i in range(count):
            timestamp = start_date + timedelta(
                days=random.randint(0, (end_date - start_date).days),
                seconds=random.randint(0, 86400)
            )

            tx_type = random.choice(self.transaction_types)

            # Vary transaction amounts based on type
            if "Transfer" in tx_type:
                amount = random.uniform(1000.0, 50000.0)
            elif "ACH" in tx_type or "Deposit" in tx_type:
                amount = random.uniform(100.0, 5000.0)
            elif "Check" in tx_type or "Payment" in tx_type:
                amount = random.uniform(500.0, 25000.0)
            elif "Fee" in tx_type:
                amount = random.uniform(5.0, 500.0)
            else:
                amount = random.uniform(100.0, 20000.0)

            # Status with varying probabilities
            if random.random() < 0.02:
                status = "disputed"
            elif random.random() < 0.95:
                status = "completed"
            else:
                status = "failed"

            tx_id = self._generate_id(f"TXN", i + 1)
            tx = Transaction(
                tx_id=tx_id,
                amount=round(amount, 2),
                timestamp=timestamp,
                description=f"{tx_type} - {random.choice(['Payment', 'Invoice #', 'Transfer to'])} {random.randint(1000, 9999)}",
                account_from=random.choice(self.accounts),
                account_to=random.choice(self.accounts),
                status=status
            )

            transactions.append(tx)

        return transactions

    def generate_bank_statement(
        self,
        statement_date: datetime,
        transactions: Optional[List[Transaction]] = None,
        closing_balance: Optional[float] = None
    ) -> BankStatement:
        """
        Generate a complete bank statement

        Args:
            statement_date: Statement date
            transactions: Optional pre-generated transactions
            closing_balance: Optional custom closing balance

        Returns:
            BankStatement object
        """
        if transactions is None:
            transactions = self.generate_transactions(count=random.randint(80, 150))

        statement_id = self._generate_id("STMT", int(statement_date.timestamp()))

        total_debits = sum(tx.amount for tx in transactions if tx.status == "completed" and tx.account_from == "system")
        total_credits = sum(tx.amount for tx in transactions if tx.status == "completed" and tx.account_to == "system")

        # Generate realistic closing balance
        if closing_balance is None:
            balance_start = random.uniform(100000.0, 500000.0)
            balance_start = round(balance_start, 2)

            balance_start, balance_end = self._calculate_balance_series(transactions)

            closing_balance = round(balance_start + balance_end, 2)

        stmt = BankStatement(
            statement_id=statement_id,
            bank_name=self.bank_name,
            start_date=statement_date - timedelta(days=30),
            end_date=statement_date,
            total_debits=round(total_debits, 2),
            total_credits=round(total_credits, 2),
            closing_balance=closing_balance,
            transactions=transactions
        )

        return stmt

    def generate_ledger_entries(
        self,
        transactions: List[Transaction]
    ) -> List[LedgerEntry]:
        """
        Generate corresponding ledger entries from transactions

        Args:
            transactions: List of transactions

        Returns:
            List of ledger entries
        """
        entries = []

        for tx in transactions:
            if tx.status != "completed":
                continue

            debit_credit = "DEBIT" if tx.account_from == "system" else "CREDIT"
            account = tx.account_to if debit_credit == "CREDIT" else tx.account_from

            entry_id = self._generate_id("LEDG", random.randint(10000, 99999))
            entry = LedgerEntry(
                entry_id=entry_id,
                tx_id=tx.tx_id,
                amount=tx.amount,
                debit_credit=debit_credit,
                account=account,
                transaction_date=tx.timestamp,
                posted_date=tx.timestamp
            )

            entries.append(entry)

        return entries

    def create_reconciliation_scenario(
        self,
        scenario_type: str = "standard",
        attack_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a complete reconciliation scenario with optional attack

        Args:
            scenario_type: Type of scenario (standard, duplicate_transactions, missing_ledger, etc.)
            attack_type: Optional attack type to inject

        Returns:
            Complete scenario with statements, ledger, and reconciliation data
        """
        today = datetime.now()

        # Generate bank statement
        bank_stmt = self.generate_bank_statement(
            statement_date=today,
            transactions=None  # Let CFOSimulator generate internally
        )

        # Generate ledger
        ledger_entries = self.generate_ledger_entries(bank_stmt.transactions)

        scenario = {
            "scenario_type": scenario_type,
            "bank_statement": bank_stmt.to_dict(),
            "ledger": [e.to_dict() for e in ledger_entries],
            "transactions": [t.to_dict() for t in bank_stmt.transactions],
            "balances": {
                "statement_balance": bank_stmt.closing_balance,
                "ledger_balance": round(sum(e.amount for e in ledger_entries), 2),
                "difference": round(bank_stmt.closing_balance - sum(e.amount for e in ledger_entries), 2)
            },
            "attack_injected": attack_type is not None
        }

        if attack_type:
            scenario["attack_info"] = {
                "type": attack_type,
                "description": f"Injected {attack_type} during reconciliation"
            }

        return scenario

    def create_scenario_with_attack(
        self,
        attack_type: str,
        attack_parameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create scenario specifically designed for attack testing

        Args:
            attack_type: Attack type from DSL (transaction_fraud, GL_mismatch, etc.)
            attack_parameters: Optional parameters to customize attack

        Returns:
            Scenario with injected attack data
        """
        today = datetime.now()

        # Generate statement
        bank_stmt = self.generate_bank_statement(
            statement_date=today,
            transactions=None
        )

        # Apply attack based on type
        if attack_type == "transaction_fraud":
            # Inject fraudulent transaction
            fraud_tx = self._create_fraudulent_transaction(attack_parameters)
            bank_stmt.transactions.append(fraud_tx)
            bank_stmt.transactions[-1].status = "completed"

        elif attack_type == "GL_mismatch":
            # Insert mismatched ledger entry
            mismatch_ledger = self._create_mismatched_ledger_entry()
            self._apply_ledger_entry(bank_stmt, mismatch_ledger)

        elif attack_type == "data_corruption":
            # Corrupt transaction amount
            if bank_stmt.transactions:
                random_tx = random.choice(bank_stmt.transactions)
                random_tx.amount *= 1.5  # Corrupt by 50%
                bank_stmt.transactions[-1] = random_tx

        scenario = {
            "scenario_type": f"attack_{attack_type}",
            "bank_statement": bank_stmt.to_dict(),
            "ledger": [e.to_dict() for e in self.generate_ledger_entries(bank_stmt.transactions)],
            "transaction_count": len(bank_stmt.transactions),
            "attack_info": {
                "type": attack_type,
                "parameters": attack_parameters or {}
            }
        }

        return scenario

    def _generate_id(self, prefix: str, sequence: int) -> str:
        """Generate standardized ID"""
        timestamp = int(datetime.now().timestamp())
        return f"{prefix}_{timestamp}_{sequence}"

    def _create_fraudulent_transaction(self, parameters: Optional[Dict] = None) -> Transaction:
        """Create a fraudulent transaction based on parameters"""
        fraud_type = parameters.get("fraud_type", "invented_credit") if parameters else "invented_credit"
        amount_range = parameters.get("amount_range", "1000..25000") if parameters else "1000..25000"
        count = parameters.get("count", 1) if parameters else 1

        min_amt, max_amt = map(float, amount_range.split('..'))

        amount = random.uniform(min_amt, max_amt)
        amount = round(amount, 2)

        return Transaction(
            tx_id=self._generate_id("FRAUD", random.randint(1000, 9999)),
            amount=amount,
            timestamp=datetime.now() - timedelta(days=random.randint(1, 30)),
            description="Fraudulent Transaction (Attack)",
            account_from="external_beneficiary",
            account_to="Primary Operating Account",
            status="completed"
        )

    def _create_mismatched_ledger_entry(self) -> LedgerEntry:
        """Create a ledger entry that doesn't match any transaction"""
        return LedgerEntry(
            entry_id=self._generate_id("LEDG", random.randint(10000, 99999)),
            tx_id="NO_MATCH_TRANSACTION",
            amount=round(random.uniform(1000.0, 10000.0), 2),
            debit_credit=random.choice(["DEBIT", "CREDIT"]),
            account=random.choice(self.accounts),
            transaction_date=datetime.now() - timedelta(days=random.randint(1, 30)),
            posted_date=datetime.now() - timedelta(days=random.randint(1, 30))
        )

    def _apply_ledger_entry(self, bank_stmt: BankStatement, ledger: LedgerEntry):
        """Apply a ledger entry to the bank statement"""
        # In a real reconciliation system, this would update balances
        # For simulation, we just keep it in the structure
        pass

    def _calculate_balance_series(self, transactions: List[Transaction]) -> tuple:
        """Calculate running balance series"""
        balance = 0.0
        balance_series = []

        for tx in transactions:
            if tx.status == "completed":
                if tx.account_from == "system":
                    balance -= tx.amount
                elif tx.account_to == "system":
                    balance += tx.amount

            balance_series.append(round(balance, 2))

        return balance_series[-1], balance_series[-1]


# Example usage and test
if __name__ == "__main__":
    # Initialize CFO Simulator
    simulator = CFOSimulator(bank_name="Acme Financial")

    # Generate standard scenario
    print("\n=== Standard Reconciliation Scenario ===")
    scenario = simulator.create_reconciliation_scenario("standard")

    print(f"Scenario Type: {scenario['scenario_type']}")
    print(f"Transaction Count: {scenario['transaction_count']}")
    print(f"Bank Statement Balance: ${scenario['balances']['statement_balance']:.2f}")
    print(f"Ledger Balance: ${scenario['balances']['ledger_balance']:.2f}")
    print(f"Difference: ${scenario['balances']['difference']:.2f}")

    # Generate attack scenario
    print("\n=== Attack Scenario: Transaction Fraud ===")
    attack_scenario = simulator.create_scenario_with_attack(
        attack_type="transaction_fraud",
        attack_parameters={"fraud_type": "unauthorized_debit", "amount_range": "5000..20000", "count": 3}
    )

    print(f"Scenario Type: {attack_scenario['scenario_type']}")
    print(f"Transaction Count (with attack): {attack_scenario['transaction_count']}")
    print(f"Attack Type: {attack_scenario['attack_info']['type']}")
    print(f"Fraudulent Amounts: ${sum(tx['amount'] for tx in attack_scenario['transactions'] if 'fraud' in tx['tx_id'].lower()):.2f}")

    # Generate complete dataset
    print("\n=== Complete Reconciliation Dataset ===")
    complete_data = simulator.create_reconciliation_scenario(
        scenario_type="complete",
        attack_type="GL_mismatch"
    )

    print(f"Statement ID: {complete_data['bank_statement']['statement_id']}")
    print(f"Bank: {complete_data['bank_statement']['bank_name']}")
    print(f"Date Range: {complete_data['bank_statement']['start_date']} to {complete_data['bank_statement']['end_date']}")
    print(f"Total Credits: ${complete_data['bank_statement']['total_credits']:.2f}")
    print(f"Total Debits: ${complete_data['bank_statement']['total_debits']:.2f}")
