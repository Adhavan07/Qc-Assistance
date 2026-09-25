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

function formatDate(isoString: string): string {
  if (!isoString) return "";
  const parts = isoString.slice(0, 10).split("-");
  if (parts.length === 3) {
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const month = months[parseInt(parts[1], 10) - 1] || parts[1];
    return `${month} ${parseInt(parts[2], 10)}, ${parts[0]}`;
  }
  return isoString.slice(0, 10);
}

export default function DashboardView({ onOpenInspector, onOpenUpload }: DashboardViewProps) {
  const recentRuns: QCRun[] = MOCK_RECENT_RUNS;

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Wiring Quality Intelligence Dashboard
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time compliance monitoring across IPC-WHMA-A-620D Class 3 and UL 508A drawing packages.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={onOpenUpload}
            id="dash-upload-btn"
            className="flex items-center space-x-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition-all cursor-pointer"
          >
            <Upload className="h-4 w-4" />
            <span>Upload Diagram Manual</span>
          </button>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* KPI 1: Total Diagrams */}
        <div className="pro-card pro-card-hover p-5 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Total Drawings Checked
            </span>
            <div className="h-9 w-9 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600">
              <FileText className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-slate-900">142</span>
            <span className="flex items-center text-xs font-semibold text-emerald-600">
              <TrendingUp className="h-3 w-3 mr-0.5" /> +14% mo/mo
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-500 font-medium">Over 3,420 connection nets inspected</p>
        </div>

        {/* KPI 2: Overall Compliance Pass Rate */}
        <div className="pro-card pro-card-hover p-5 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Pass Rate (First Pass Yield)
            </span>
            <div className="h-9 w-9 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-slate-900">88.4%</span>
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              Target: 85%
            </span>
          </div>
          <div className="mt-3 w-full bg-slate-100 rounded-full h-2 overflow-hidden">
            <div className="bg-emerald-500 h-2 rounded-full" style={{ width: "88.4%" }}></div>
          </div>
        </div>

        {/* KPI 3: Open Discrepancies */}
        <div className="pro-card pro-card-hover p-5 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Active Findings
            </span>
            <div className="h-9 w-9 rounded-lg bg-red-50 border border-red-100 flex items-center justify-center text-red-600">
              <AlertTriangle className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-red-600">29</span>
            <span className="text-xs font-medium text-slate-500">across 4 projects</span>
          </div>
          <div className="mt-2 flex items-center space-x-2 text-[11px]">
            <span className="text-red-700 font-bold bg-red-50 px-1.5 py-0.5 rounded border border-red-200">3 Critical</span>
            <span className="text-amber-700 font-bold bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">8 Major</span>
            <span className="text-yellow-800 font-bold bg-yellow-50 px-1.5 py-0.5 rounded border border-yellow-200">14 Minor</span>
          </div>
        </div>

        {/* KPI 4: Mean Inspection Latency */}
        <div className="pro-card pro-card-hover p-5 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Avg. Engine Turnaround
            </span>
            <div className="h-9 w-9 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-slate-900">1.84s</span>
            <span className="text-xs font-medium text-indigo-600">per drawing sheet</span>
          </div>
          <p className="mt-2 text-xs text-slate-500 font-medium">Zero false alarms on wire tags</p>
        </div>
      </div>

      {/* Middle Grid: Category Breakdown & Standards Adherence */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Defect Categories */}
        <div className="lg:col-span-2 pro-card p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Defect Breakdown by Rule Category
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Distribution of findings caught by deterministic rules & multimodal validation
              </p>
            </div>
            <span className="text-xs text-blue-700 font-mono bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200 font-semibold">
              100% Deterministic Verification
            </span>
          </div>

          <div className="space-y-4 pt-2">
            {[
              { label: "Wire Sizing & Breaker Mismatch (RULE-WIRE-001)", count: 9, percentage: 31, color: "bg-red-500", text: "text-red-700" },
              { label: "Connector Pin & Contact Gauge Mismatch (RULE-CONN-002)", count: 7, percentage: 24, color: "bg-amber-500", text: "text-amber-700" },
              { label: "Minimum Bend Radius Violations (RULE-BEND-001)", count: 5, percentage: 17, color: "bg-orange-500", text: "text-orange-700" },
              { label: "AC/DC Insulation Color Coding (RULE-COLOR-003)", count: 5, percentage: 17, color: "bg-yellow-500", text: "text-yellow-700" },
              { label: "Terminal Lug Torque & Busbar Annotations (RULE-TERM-004)", count: 3, percentage: 11, color: "bg-blue-500", text: "text-blue-700" },
            ].map((cat, idx) => (
              <div key={idx} className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-700 font-semibold">{cat.label}</span>
                  <span className={`font-mono font-bold ${cat.text}`}>{cat.count} issues ({cat.percentage}%)</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div className={`${cat.color} h-2 rounded-full`} style={{ width: `${cat.percentage}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Col: Active Standards Compliance Gauge */}
        <div className="pro-card p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Standards Adherence
            </h3>
            <ShieldCheck className="h-4 w-4 text-blue-600" />
          </div>

          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-bold text-xs text-slate-900">IPC-WHMA-A-620D</div>
                  <div className="text-[11px] text-slate-500">Class 3 (Aerospace & Military)</div>
                </div>
                <span className="font-mono text-sm font-bold text-emerald-600">94.2%</span>
              </div>
              <div className="mt-2.5 w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: "94.2%" }}></div>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-bold text-xs text-slate-900">UL 508A</div>
                  <div className="text-[11px] text-slate-500">Industrial Control Panels</div>
                </div>
                <span className="font-mono text-sm font-bold text-emerald-600">91.8%</span>
              </div>
              <div className="mt-2.5 w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: "91.8%" }}></div>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-bold text-xs text-slate-900">MIL-STD-681D</div>
                  <div className="text-[11px] text-slate-500">Lead Wire Color Coding</div>
                </div>
                <span className="font-mono text-sm font-bold text-blue-600">98.5%</span>
              </div>
              <div className="mt-2.5 w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                <div className="bg-blue-600 h-1.5 rounded-full" style={{ width: "98.5%" }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Table: Recent QC Runs */}
      <div className="pro-card overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Recent Diagram QC Runs
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Click on any inspection to launch the interactive split-screen viewer
            </p>
          </div>
          <button
            onClick={() => onOpenInspector(recentRuns[0].id)}
            className="text-xs text-blue-600 hover:text-blue-700 font-semibold flex items-center space-x-1 cursor-pointer"
          >
            <span>Open Latest Inspection</span>
            <ArrowUpRight className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 uppercase text-[11px] border-b border-slate-200 font-semibold">
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
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {recentRuns.map((run) => {
                const isFail = run.overall_status === "FAIL";
                const isPass = run.overall_status === "PASS";
                return (
                  <tr
                    key={run.id}
                    onClick={() => onOpenInspector(run.id)}
                    className="hover:bg-blue-50/40 transition-colors cursor-pointer group"
                  >
                    <td className="py-3.5 px-5 font-semibold text-slate-900 flex items-center space-x-2">
                      <FileText className="h-4 w-4 text-blue-600 group-hover:scale-105 transition-transform" />
                      <span className="group-hover:text-blue-600 transition-colors">{run.document_name}</span>
                    </td>
                    <td className="py-3.5 px-5">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full font-bold text-[10px] tracking-wide uppercase border ${
                          isPass
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : isFail
                            ? "bg-red-50 text-red-700 border-red-200"
                            : "bg-amber-50 text-amber-800 border-amber-200"
                        }`}
                      >
                        {run.overall_status}
                      </span>
                    </td>
                    <td className="py-3.5 px-5 font-mono font-medium">
                      {run.checks_passed} / {run.checks_total}
                    </td>
                    <td className="py-3.5 px-5">
                      {run.checks_failed > 0 ? (
                        <span className="font-semibold text-red-600">
                          {run.checks_failed} failed {run.checks_review > 0 ? `(${run.checks_review} review)` : ""}
                        </span>
                      ) : (
                        <span className="text-emerald-600 font-semibold">0 Defects</span>
                      )}
                    </td>
                    <td className="py-3.5 px-5 font-mono text-slate-500">
                      {run.processing_time_ms} ms
                    </td>
                    <td className="py-3.5 px-5 text-slate-500">
                      {formatDate(run.created_at)}
                    </td>
                    <td className="py-3.5 px-5 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenInspector(run.id);
                        }}
                        className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 text-xs font-semibold transition-all cursor-pointer"
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
