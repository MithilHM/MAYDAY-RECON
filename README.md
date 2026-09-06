# MAYDAY RECON

Attack-based reconciliation testing framework for detecting vulnerabilities in financial reconciliation systems.

## Overview

MAYDAY RECON is a comprehensive framework designed to test reconciliation systems by systematically injecting known attack patterns and monitoring for detection failures. It helps organizations proactively identify and remediate security weaknesses in their financial reconciliation processes.

## Core Components

### Attack DSL
The Attack Definition Language (DSL) defines attack patterns, their execution stages, and expected detection behaviors. Located in `mayday/attack.dsl.yml`.

### ReconBot
An intelligent orchestrator agent that manages the entire reconciliation testing lifecycle:
- Loads and parses attack definitions
- Injects attacks at configured stages
- Monitors for detection failures
- Generates comprehensive test reports

### CFO Simulator
A financial transaction simulator that generates realistic bank statements and transaction data:
- Generates realistic transaction patterns
- Creates bank statements for testing
- Supports various account types and transaction scenarios

### Reconciliation Engine
Orchestrates the complete reconciliation workflow:
- Runs multi-stage reconciliation tests
- Injects attacks at specific stages
- Tracks detection and resolution
- Generates detailed reports

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/MithilHM/MAYDAY-RECON.git
cd MAYDAY-RECON

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Basic Usage

```python
from mayday.reconciliation_engine import ReconciliationEngine

# Initialize the engine
engine = ReconciliationEngine()
engine.initialize_from_dsl()

# Run a reconciliation test
test_report = engine.run_reconciliation_test(
    test_name="test-standard-transactions",
    attack_filters=None,
    severity_threshold="low"
)

# Generate a human-readable report
report = engine.generate_reconciliation_report(test_report)
```

### Running Integration Tests

```bash
# Run all integration tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=mayday --cov-report=html

# Run specific test file
pytest tests/test_integration.py
```

## Attack DSL Structure

The Attack DSL (`mayday/attack.dsl.yml`) defines attack patterns with the following structure:

```yaml
attack_definitions:
  - attack_name: "transaction_fraud"
    description: "Inject fraudulent transaction data"
    type: "data_corruption"
    severity: "medium"
    stage: "validate"
    method: "currency_swap"
    parameters:
      allowed_currencies: ["USD", "EUR"]
      fraud_percentage: 5.0
    tags:
      - "transaction"
      - "fraud"
      - "validation"
```

## Supported Attacks

### Transaction Fraud
- Currency swap attacks
- Amount manipulation
- Transaction timing attacks
- Duplicate transaction detection bypass

### GL (General Ledger) Attacks
- Mismatch detection bypass
- Account code injection
- Transaction categorization attacks
- Reconciliation rules evasion

### System Integrity Attacks
- Data corruption patterns
- State manipulation attacks
- Detection logic bypasses
- Boundary condition exploits

## Test Suite

The framework automatically generates comprehensive test suites from attack definitions:

```python
# Generate test suite from all attack definitions
test_suite = engine.generate_test_suite()

# Save to YAML file
with open('test_suite.yaml', 'w') as f:
    yaml.dump(test_suite, f)
```

## Output Formats

### Console Output

Detailed progress tracking during test execution:
```
============================================================
Running Reconciliation Test: test-standard-transactions
============================================================

Stage: LOAD
------------------------------------------------------------
Injecting 3 attacks at load stage
  ✓ Injected: transaction_fraud -> 1/3
  ✓ Injected: GL_mismatch -> 2/3
  ✓ Injected: detection_bypass -> 3/3
  Transactions Processed: 234

⚠ Detected 2 attacks at load
============================================================
```

### Report Format

Human-readable text report with:
- Test metadata and status
- Stage-by-stage execution results
- Attack injection and detection counts
- Reconciliation metrics

## Project Structure

```
MAYDAY-RECON/
├── mayday/
│   ├── attack.dsl.yml              # Attack definitions DSL
│   ├── agents/
│   │   └── reconbot.py            # ReconBot orchestration agent
│   ├── __init__.py
│   ├── cfo_simulator.py           # CFO simulation engine
│   ├── reconciliation_engine.py   # Main reconciliation orchestrator
│   └── __init__.py
├── simulator/
│   ├── cfo-simulator.py           # CFO simulation module
│   └── __init__.py
├── db/
│   └── __init__.py
├── tests/
│   ├── __init__.py
│   └── test_integration.py        # Integration test suite
├── apps/
│   ├── api/                       # FastAPI backend (scaffold)
│   └── web/                       # Next.js frontend (scaffold)
├── pyproject.toml                 # Project configuration
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## API Reference

### ReconciliationEngine

**`__init__(dsl_path: str = "mayday/attack.dsl.yml")`**
- Initialize engine with DSL file path

**`initialize_from_dsl(dsl_path: str)`**
- Load and parse attack definitions from DSL

**`run_reconciliation_test(test_name: str, attack_filters: List[str], severity_threshold: str)`**
- Run complete reconciliation test with attack injection

**`generate_reconciliation_report(test_report: Dict, output_path: Optional[str])`**
- Generate human-readable report

**`load_dsl(dsl_path: str)`**
- Load and validate DSL file

**`generate_test_suite(output_file: str)`**
- Generate test suite configuration from attacks

### ReconBot

**`inject_attack(attack_name: str, parameters: Dict)`**
- Inject a specific attack into reconciliation process

**`start_reconciliation_session(session_id: str, attack_filters: List[str])`**
- Start new reconciliation session

**`end_session()`**
- End current session and generate summary

### CFOSimulator

**`generate_transactions(transaction_count: int, account_type: str, date_range_days: int)`**
- Generate test transactions

**`generate_bank_statement(account_id: str, date_range: Tuple[str, str])`**
- Generate complete bank statement

## Contributing

### Code Style

- Follow PEP 8 guidelines
- Use `black` for code formatting: `black mayday/ tests/`
- Use `isort` for import organization: `isort mayday/ tests/`

### Testing

1. Write tests for new functionality
2. Ensure all tests pass: `pytest tests/`
3. Generate coverage reports: `pytest tests/ --cov=mayday`

### Adding New Attacks

1. Add attack definition to `mayday/attack.dsl.yml`
2. Define attack parameters and expected behavior
3. Update tests for new attack scenarios
4. Generate new test suite

## Development Workflow

```bash
# Clone the repository
git clone https://github.com/MithilHM/MAYDAY-RECON.git
cd MAYDAY-RECON

# Create feature branch
git checkout -b feature/new-attack

# Make changes
# - Update attack.dsl.yml
# - Implement attack logic
# - Write tests

# Run tests
pytest tests/

# Format code
black mayday/ tests/
isort mayday/ tests/

# Commit changes
git add .
git commit -m "feat: add new attack type"

# Push and create PR
git push origin feature/new-attack
```

## Security Considerations

- This framework is designed for security testing only
- Never use attack patterns on production systems
- Ensure proper authorization before testing
- Follow organizational security policies

## License

MIT License - See LICENSE file for details

## Team

- **MithilHM** - Project Lead and Core Developer

## Version History

- **v1.0.0** (2026-09-06): Initial release with core framework components
  - ReconBot agent implementation
  - CFO Simulator
  - Reconciliation Engine
  - Integration test suite
  - Attack DSL framework

## Acknowledgments

- Built with support from AOHacks community
- Inspired by industry-standard reconciliation testing practices

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/MithilHM/MAYDAY-RECON/issues
- Documentation: https://github.com/MithilHM/MAYDAY-RECON/blob/main/README.md
