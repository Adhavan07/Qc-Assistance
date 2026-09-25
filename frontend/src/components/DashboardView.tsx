"use client";

import React from "react";
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowUpRight,
  TrendingUp,
  ShieldCheck,
  ChevronRight,
  Upload,
} from "lucide-react";
import { QCRun } from "../types";
import { MOCK_RECENT_RUNS } from "../lib/mockData";

interface DashboardViewProps {
  onOpenInspector: (runId: string) => void;
  onOpenUpload: () => void;
}

export default function DashboardView({ onOpenInspector, onOpenUpload }: DashboardViewProps) {
  const recentRuns: QCRun[] = MOCK_RECENT_RUNS;

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/10">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Wiring Quality Intelligence Dashboard
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time compliance monitoring across IPC-WHMA-A-620D Class 3 and UL 508A drawing packages.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={onOpenUpload}
            id="dash-upload-btn"
            className="flex items-center space-x-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-cyan-600/20 hover:from-cyan-500 hover:to-blue-500 transition-all hover:scale-[1.02]"
          >
            <Upload className="h-4 w-4" />
            <span>Upload Diagram Manual</span>
          </button>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* KPI 1: Total Diagrams */}
        <div className="glass-panel p-5 relative overflow-hidden group hover:border-cyan-500/40 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Total Drawings Checked
            </span>
            <div className="h-9 w-9 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <FileText className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-white">142</span>
            <span className="flex items-center text-xs font-medium text-emerald-400">
              <TrendingUp className="h-3 w-3 mr-0.5" /> +14% mo/mo
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-400">Over 3,420 connection nets inspected</p>
        </div>

        {/* KPI 2: Overall Compliance Pass Rate */}
        <div className="glass-panel p-5 relative overflow-hidden group hover:border-emerald-500/40 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Pass Rate (First Pass Yield)
            </span>
            <div className="h-9 w-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-white">88.4%</span>
            <span className="text-xs font-medium text-emerald-400">Target: 85.0%</span>
          </div>
          <div className="mt-3 w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: "88.4%" }}></div>
          </div>
        </div>

        {/* KPI 3: Open Discrepancies */}
        <div className="glass-panel p-5 relative overflow-hidden group hover:border-rose-500/40 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Active Findings
            </span>
            <div className="h-9 w-9 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
              <AlertTriangle className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-rose-400">29</span>
            <span className="text-xs font-medium text-slate-400">across 4 projects</span>
          </div>
          <div className="mt-2 flex items-center space-x-2 text-[11px]">
            <span className="text-rose-400 font-semibold">3 Critical</span>
            <span className="text-slate-600">•</span>
            <span className="text-orange-400 font-semibold">8 Major</span>
            <span className="text-slate-600">•</span>
            <span className="text-amber-400 font-semibold">14 Minor</span>
          </div>
        </div>

        {/* KPI 4: Mean Inspection Latency */}
        <div className="glass-panel p-5 relative overflow-hidden group hover:border-blue-500/40 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Avg. Engine Turnaround
            </span>
            <div className="h-9 w-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-white">1.84s</span>
            <span className="text-xs font-medium text-cyan-400">per drawing sheet</span>
          </div>
          <p className="mt-2 text-xs text-slate-400">Zero false alarms on wire tags</p>
        </div>
      </div>

      {/* Middle Grid: Category Breakdown & Standards Adherence */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Defect Categories */}
        <div className="lg:col-span-2 glass-panel p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                Defect Breakdown by Rule Category
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Distribution of findings caught by deterministic rules & multimodal validation
              </p>
            </div>
            <span className="text-xs text-cyan-400 font-mono bg-cyan-500/10 px-2.5 py-1 rounded-md border border-cyan-500/20">
              100% Deterministic Verification
            </span>
          </div>

          <div className="space-y-4 pt-2">
            {[
              { label: "Wire Sizing & Breaker Mismatch (RULE-WIRE-001)", count: 9, percentage: 31, color: "bg-red-500", text: "text-red-400" },
              { label: "Connector Pin & Contact Gauge Mismatch (RULE-CONN-002)", count: 7, percentage: 24, color: "bg-orange-500", text: "text-orange-400" },
              { label: "Minimum Bend Radius Violations (RULE-BEND-001)", count: 5, percentage: 17, color: "bg-amber-500", text: "text-amber-400" },
              { label: "AC/DC Insulation Color Coding (RULE-COLOR-003)", count: 5, percentage: 17, color: "bg-yellow-500", text: "text-yellow-400" },
              { label: "Terminal Lug Torque & Busbar Annotations (RULE-TERM-004)", count: 3, percentage: 11, color: "bg-sky-500", text: "text-sky-400" },
            ].map((cat, idx) => (
              <div key={idx} className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">{cat.label}</span>
                  <span className={`font-mono font-bold ${cat.text}`}>{cat.count} issues ({cat.percentage}%)</span>
                </div>
                <div className="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden">
                  <div className={`${cat.color} h-2 rounded-full`} style={{ width: `${cat.percentage}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Col: Active Standards Compliance Gauge */}
        <div className="glass-panel p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Standards Adherence
            </h3>
            <ShieldCheck className="h-4 w-4 text-cyan-400" />
          </div>

          <div className="space-y-4">
            <div className="rounded-xl border border-white/5 bg-slate-900/60 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold text-xs text-white">IPC-WHMA-A-620D</div>
                  <div className="text-[11px] text-slate-400">Class 3 (Aerospace & Military)</div>
                </div>
                <span className="font-mono text-sm font-bold text-emerald-400">94.2%</span>
              </div>
              <div className="mt-2.5 w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: "94.2%" }}></div>
              </div>
            </div>

            <div className="rounded-xl border border-white/5 bg-slate-900/60 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold text-xs text-white">UL 508A</div>
                  <div className="text-[11px] text-slate-400">Industrial Control Panels</div>
                </div>
                <span className="font-mono text-sm font-bold text-emerald-400">91.8%</span>
              </div>
              <div className="mt-2.5 w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: "91.8%" }}></div>
              </div>
            </div>

            <div className="rounded-xl border border-white/5 bg-slate-900/60 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold text-xs text-white">MIL-STD-681D</div>
                  <div className="text-[11px] text-slate-400">Lead Wire Color Coding</div>
                </div>
                <span className="font-mono text-sm font-bold text-cyan-400">98.5%</span>
              </div>
              <div className="mt-2.5 w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div className="bg-cyan-500 h-1.5 rounded-full" style={{ width: "98.5%" }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Table: Recent QC Runs */}
      <div className="glass-panel overflow-hidden">
        <div className="p-5 border-b border-white/10 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Recent Diagram QC Runs
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Click on any inspection to launch the interactive split-screen viewer
            </p>
          </div>
          <button
            onClick={() => onOpenInspector(recentRuns[0].id)}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold flex items-center space-x-1"
          >
            <span>Open Latest Inspection</span>
            <ArrowUpRight className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/60 text-slate-400 uppercase text-[11px] border-b border-white/5">
              <tr>
                <th className="py-3 px-5">Document Name</th>
                <th className="py-3 px-5">Status</th>
                <th className="py-3 px-5">Checks Passed</th>
                <th className="py-3 px-5">Discrepancies</th>
                <th className="py-3 px-5">Inspection Time</th>
                <th className="py-3 px-5">Date</th>
                <th className="py-3 px-5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {recentRuns.map((run) => {
                const isFail = run.overall_status === "FAIL";
                const isPass = run.overall_status === "PASS";
                return (
                  <tr
                    key={run.id}
                    onClick={() => onOpenInspector(run.id)}
                    className="hover:bg-cyan-500/5 transition-colors cursor-pointer group"
                  >
                    <td className="py-3.5 px-5 font-medium text-white flex items-center space-x-2">
                      <FileText className="h-4 w-4 text-cyan-400 group-hover:scale-110 transition-transform" />
                      <span className="group-hover:text-cyan-300 transition-colors">{run.document_name}</span>
                    </td>
                    <td className="py-3.5 px-5">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full font-bold text-[10px] tracking-wide uppercase border ${
                          isPass
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                            : isFail
                            ? "bg-rose-500/10 text-rose-400 border-rose-500/30 glow-critical"
                            : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                        }`}
                      >
                        {run.overall_status}
                      </span>
                    </td>
                    <td className="py-3.5 px-5 font-mono">
                      {run.checks_passed} / {run.checks_total}
                    </td>
                    <td className="py-3.5 px-5">
                      {run.checks_failed > 0 ? (
                        <span className="font-semibold text-rose-400">
                          {run.checks_failed} failed {run.checks_review > 0 ? `(${run.checks_review} review)` : ""}
                        </span>
                      ) : (
                        <span className="text-emerald-400 font-semibold">0 Defects</span>
                      )}
                    </td>
                    <td className="py-3.5 px-5 font-mono text-slate-400">
                      {run.processing_time_ms} ms
                    </td>
                    <td className="py-3.5 px-5 text-slate-400">
                      {new Date(run.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-5 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenInspector(run.id);
                        }}
                        className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20 border border-cyan-500/30 text-xs font-semibold transition-all"
                      >
                        <span>Inspect</span>
                        <ChevronRight className="h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
