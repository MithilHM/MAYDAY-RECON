"""
MAYDAY Intervention Engine module.
Generates candidate repair interventions (PROMPT, TOOL, WORKFLOW, POLICY, MEMORY),
evaluates candidates empirically against the regression suite, and selects the optimal verified fix.
"""
from typing import Dict, List, Any, Optional
import concurrent.futures
import os
import tempfile

class InterventionEngine:
    def generate_candidates(self, failure_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        missing_behavior = failure_report.get("missing_behavior")
        attack_id = failure_report.get("attack_id")

        candidates = []

        # Candidate A: Prompt Patch Intervention
        candidates.append({
            "id": f"INT-PROMPT-{attack_id}",
            "type": "prompt",
            "name": f"Prompt Patch: Enforce {missing_behavior}",
            "instruction": f"SYSTEM PROMPT: Always check for {missing_behavior} before mutating financial state.",
            "estimated_impact": "PROMPT_ONLY"
        })

        # Candidate B: Verification Tool Intervention
        candidates.append({
            "id": f"INT-TOOL-{attack_id}",
            "type": "tool",
            "name": "Verification Tool: Add Postcondition Verifier",
            "tool": "postcondition_verifier",
            "estimated_impact": "TOOL_VERIFICATION"
        })

        # Candidate C: Workflow Guard Intervention
        candidates.append({
            "id": f"INT-WORKFLOW-{attack_id}",
            "type": "workflow",
            "name": f"Workflow Guard: Add {missing_behavior} Checkpoint",
            "guard": missing_behavior,
            "estimated_impact": "WORKFLOW_CHECKPOINT"
        })

        # Candidate D: Memory Rule Intervention
        candidates.append({
            "id": f"INT-MEMORY-{attack_id}",
            "type": "memory",
            "name": f"Reliability Memory Rule: Remember {missing_behavior}",
            "rule": missing_behavior,
            "estimated_impact": "MEMORY_PATTERNS"
        })

        # Candidate E: Policy Rule Intervention
        candidates.append({
            "id": f"INT-POLICY-{attack_id}",
            "type": "policy",
            "name": f"Policy Rule: Enforce {missing_behavior} guard",
            "policy_patch": (
                f"POLICY PATCH: Require REVIEW on cross_period and duplicate "
                f"ambiguity before auto-reconcile; enforce {missing_behavior}."
            ),
            "estimated_impact": "POLICY_GUARD"
        })

        return candidates

    def evaluate_candidates(
        self,
        candidates: List[Dict[str, Any]],
        attack_spec: Dict[str, Any],
        base_version: str = "v0.1",
        parallel: bool = True,
        max_workers: int = 4,
    ) -> Dict[str, Dict[str, Any]]:
        """Empirically test each candidate on origin attack + full suite.

        Returns {candidate_id: {origin_far, regression_pass_rate,
        creates_new_failure}} where creates_new_failure is True when the
        candidate turns a baseline-PASS attack into FAIL.
        """
        # Local imports to avoid circulars at module load.
        from simulator.seed.seed_data import seed_database
        from simulator.db.database import DB_FILE
        from mayday.gateway.tool_gateway import ToolGateway
        from agent.reconbot import ReconBot
        from mayday.evaluator.deterministic_evaluator import DeterministicEvaluator
        from mayday.attacks.attack_registry import list_all_attacks

        try:
            from mayday.regression.regression_engine import RegressionEngine
            reg_specs = RegressionEngine().load_regressions()
        except Exception:
            reg_specs = []
        suite = list_all_attacks()
        if reg_specs:
            seen = {a.get("id") for a in suite}
            for r in reg_specs:
                oid = r.get("origin_attack_id", r.get("id"))
                if oid not in seen:
                    suite = suite + [{
                        "id": oid,
                        "name": r.get("id", oid),
                        "expected": r.get("expected", {}),
                        "financial_risk": {"amount": 12450.0},
                        "target": r.get("target", {"txn_id": "TXN-1847"}),
                        "setup": r.get("setup", {}),
                    }]
                    seen.add(oid)

        def _run(attack: Dict[str, Any], version: str,
                 interventions: List[Dict[str, Any]]):
            seed_database(DB_FILE)
            gateway = ToolGateway(db_path=DB_FILE, active_attack=attack)
            bot = ReconBot(gateway=gateway, version=version,
                           interventions=interventions)
            txn_id = attack.get("target", {}).get("txn_id", "TXN-1847")
            try:
                res = bot.reconcile_transaction(txn_id)
            except Exception as e:
                res = {"decision": "BLOCK", "reason": str(e)}
            ev = DeterministicEvaluator(attack, gateway.trace_logs, res).evaluate()
            return ev

        def _run_isolated(attack: Dict[str, Any], version: str,
                          interventions: List[Dict[str, Any]]):
            # Thread-safe: each run gets its own tmp SQLite file so no
            # concurrent writes ever hit the shared DB_FILE.
            fd, tmp = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            try:
                seed_database(tmp)
                gateway = ToolGateway(db_path=tmp, active_attack=attack)
                bot = ReconBot(gateway=gateway, version=version,
                               interventions=interventions)
                txn_id = attack.get("target", {}).get("txn_id", "TXN-1847")
                try:
                    res = bot.reconcile_transaction(txn_id)
                except Exception as e:
                    res = {"decision": "BLOCK", "reason": str(e)}
                ev = DeterministicEvaluator(
                    attack, gateway.trace_logs, res).evaluate()
                return ev
            finally:
                try:
                    os.remove(tmp)
                except OSError:
                    pass

        def _result_entry(origin_ev: Dict[str, Any], suite_evs: List[Dict[str, Any]],
                          baseline_outcome: Dict[str, str]) -> Dict[str, Any]:
            passed = sum(1 for ev in suite_evs if ev.get("outcome") == "PASS")
            new_failure = any(
                ev.get("outcome") != "PASS"
                and baseline_outcome.get(attack["id"]) == "PASS"
                for attack, ev in zip(suite, suite_evs)
            )
            return {
                "origin_far": origin_ev.get("far_score", 0.0),
                "far_score": origin_ev.get("far_score", 0.0),
                "origin_outcome": origin_ev.get("outcome", "FAIL"),
                "regression_pass_rate": round(passed / len(suite), 3) if suite else 0.0,
                "creates_new_failure": new_failure,
            }

        if not parallel:
            baseline_outcome = {
                a["id"]: _run(a, base_version, []).get("outcome", "FAIL")
                for a in suite
            }

            results: Dict[str, Dict[str, Any]] = {}
            for cand in candidates:
                origin_ev = _run(attack_spec, base_version, [cand])
                passed = 0
                new_failure = False
                for attack in suite:
                    ev = _run(attack, base_version, [cand])
                    if ev.get("outcome") == "PASS":
                        passed += 1
                    elif baseline_outcome.get(attack["id"]) == "PASS":
                        new_failure = True
                results[cand["id"]] = {
                    "origin_far": origin_ev.get("far_score", 0.0),
                    "far_score": origin_ev.get("far_score", 0.0),
                    "origin_outcome": origin_ev.get("outcome", "FAIL"),
                    "regression_pass_rate": round(passed / len(suite), 3) if suite else 0.0,
                    "creates_new_failure": new_failure,
                }
            return results

        workers = max(1, max_workers or 1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            base_futs = {
                ex.submit(_run_isolated, a, base_version, []): a for a in suite
            }
            baseline_outcome = {}
            for fut, attack in base_futs.items():
                try:
                    baseline_outcome[attack["id"]] = fut.result().get("outcome", "FAIL")
                except Exception:
                    baseline_outcome[attack["id"]] = "FAIL"

            results = {}
            for cand in candidates:
                origin_fut = ex.submit(_run_isolated, attack_spec, base_version, [cand])
                suite_futs = [
                    ex.submit(_run_isolated, attack, base_version, [cand])
                    for attack in suite
                ]
                origin_ev = origin_fut.result()
                suite_evs = [f.result() for f in suite_futs]
                results[cand["id"]] = _result_entry(origin_ev, suite_evs, baseline_outcome)
        return results

    def select_best_intervention(
        self,
        candidates: List[Dict[str, Any]],
        eval_results_map: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Selects candidate with the highest empirical FAR score on the regression suite.
        Accepts float scores (legacy) or dicts {origin_far, regression_pass_rate,
        creates_new_failure}. Candidates that create new failures are rejected
        unless every candidate does.
        """
        def _score(v: Any) -> float:
            if isinstance(v, dict):
                for k in ("origin_far", "far_score", "score", "measured_far_score"):
                    if isinstance(v.get(k), (int, float)):
                        return float(v[k])
                if isinstance(v.get("regression_pass_rate"), (int, float)):
                    return float(v["regression_pass_rate"]) * 100.0
                return 0.0
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        def _new_failure(v: Any) -> bool:
            return bool(isinstance(v, dict) and v.get("creates_new_failure", False))

        scored = [
            (c, _score(eval_results_map.get(c["id"], 0.0)),
             _new_failure(eval_results_map.get(c["id"], 0.0)))
            for c in candidates
        ]
        safe_pool = [(c, s) for c, s, f in scored if not f]
        pool = safe_pool if safe_pool else [(c, s) for c, s, _ in scored]

        best_candidate = None
        best_score = -1.0

        for candidate, score in pool:
            candidate["measured_far_score"] = score
            if score > best_score:
                best_score = score
                best_candidate = candidate

        return best_candidate or candidates[0]
