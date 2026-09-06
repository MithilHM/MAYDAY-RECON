"use client";

import { useEffect, useState } from "react";

interface SuiteMetrics {
  agent_version: string;
  suite_type: string;
  total_scenarios: number;
  passed_scenarios: number;
  accuracy_pct: number;
  average_far_score: number;
  total_unsafe_mutations: number;
  production_ready: boolean;
  duration_seconds: number;
}

interface Overview {
  target_agent: string;
  reliability_score: number;
  adversarial_reliability: number;
  recovery_rate: number;
  policy_compliance: number;
  unsafe_mutations: number;
  cost_per_task_inr: number;
  latency_seconds: number;
  v1_metrics: SuiteMetrics;
  v2_metrics: SuiteMetrics;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/overview`)
      .then((res) => {
        if (!res.ok) throw new Error(`API ${res.status}`);
        return res.json();
      })
      .then((json: Overview) => setData(json))
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center p-24">
        <p className="text-red-400">Failed to load overview: {error}</p>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center p-24">
        <p className="text-gray-400">Loading live benchmark metrics…</p>
      </main>
    );
  }

  const { v1_metrics: v1, v2_metrics: v2 } = data;
  const accDelta = v2.accuracy_pct - v1.accuracy_pct;
  const farDelta = v2.average_far_score - v1.average_far_score;
  const unsafeDelta = v2.total_unsafe_mutations - v1.total_unsafe_mutations;

  return (
    <main className="flex min-h-screen flex-col items-center p-12">
      <div className="z-10 max-w-5xl w-full">
        <h1 className="text-4xl font-bold mb-2">MAYDAY RECON</h1>
        <p className="text-lg text-gray-400 mb-8">
          Target: {data.target_agent} · live benchmark data
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="rounded-xl bg-white/5 p-6">
            <div className="text-sm text-gray-400">Finance Reliability (FAR)</div>
            <div className="text-4xl font-bold text-blue-400">
              {data.reliability_score}
              <span className="text-base font-normal text-gray-500">/100</span>
            </div>
          </div>
          <div className="rounded-xl bg-white/5 p-6">
            <div className="text-sm text-gray-400">Adversarial Reliability</div>
            <div className="text-4xl font-bold text-emerald-400">
              {data.adversarial_reliability}%
            </div>
          </div>
          <div className="rounded-xl bg-white/5 p-6">
            <div className="text-sm text-gray-400">Unsafe Mutations</div>
            <div className="text-4xl font-bold text-emerald-400">
              {data.unsafe_mutations}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              ₹{data.cost_per_task_inr} / {data.latency_seconds}s ·{" "}
              {data.policy_compliance}% compliance
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-white/5 p-6">
          <h2 className="text-lg font-bold mb-4">
            ReconBot v0.1 vs ReconBot v0.2
          </h2>
          <table className="w-full text-left text-sm">
            <thead className="text-gray-400 uppercase text-xs">
              <tr>
                <th className="p-3">Metric</th>
                <th className="p-3">v0.1 Baseline</th>
                <th className="p-3">v0.2 Patched</th>
                <th className="p-3">Delta</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              <tr>
                <td className="p-3">Accuracy</td>
                <td className="p-3">{v1.accuracy_pct}%</td>
                <td className="p-3 font-bold">{v2.accuracy_pct}%</td>
                <td className="p-3">
                  {accDelta >= 0 ? "+" : ""}
                  {accDelta.toFixed(1)}%
                </td>
              </tr>
              <tr>
                <td className="p-3">Avg FAR</td>
                <td className="p-3">{v1.average_far_score}</td>
                <td className="p-3 font-bold">{v2.average_far_score}</td>
                <td className="p-3">
                  {farDelta >= 0 ? "+" : ""}
                  {farDelta.toFixed(1)}
                </td>
              </tr>
              <tr>
                <td className="p-3">Unsafe mutations</td>
                <td className="p-3">{v1.total_unsafe_mutations}</td>
                <td className="p-3 font-bold">{v2.total_unsafe_mutations}</td>
                <td className="p-3">{unsafeDelta}</td>
              </tr>
              <tr>
                <td className="p-3">Passed</td>
                <td className="p-3">
                  {v1.passed_scenarios}/{v1.total_scenarios}
                </td>
                <td className="p-3 font-bold">
                  {v2.passed_scenarios}/{v2.total_scenarios}
                </td>
                <td className="p-3">
                  {v2.passed_scenarios - v1.passed_scenarios} scenarios
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
