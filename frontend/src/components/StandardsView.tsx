"use client";

import React, { useState } from "react";
import { ShieldCheck, Sliders, CheckCircle2, Search } from "lucide-react";
import { MOCK_STANDARDS } from "../lib/mockData";

export default function StandardsView() {
  const [standards, setStandards] = useState(MOCK_STANDARDS);
  const [activeStandardId, setActiveStandardId] = useState("ipc-whma-a-620d");
  const [searchQuery, setSearchQuery] = useState("");

  const rules = [
    {
      id: "RULE-WIRE-001",
      standardId: "ipc-whma-a-620d",
      name: "Conductor Gauge Callout & Breaker Sizing",
      severity: "CRITICAL",
      clause: "§13.4.1 (Conductor Protection)",
      description: "Verifies every wire run has an explicit AWG callout and matches circuit breaker overcurrent rating.",
      parameter: "Min Breaker Margin: 125%",
      active: true,
    },
    {
      id: "RULE-CONN-002",
      standardId: "ipc-whma-a-620d",
      name: "Connector Contact Pin Size Matching",
      severity: "MAJOR",
      clause: "§9.2.3 (Contact Retention & Cavities)",
      description: "Validates that pin and socket contact gauges match across mated connector interfaces.",
      parameter: "Zero gauge deviation allowed",
      active: true,
    },
    {
      id: "RULE-BEND-001",
      standardId: "ipc-whma-a-620d",
      name: "Minimum Harness Bend Radius",
      severity: "MAJOR",
      clause: "§13.1.2 (Bend Radius Criteria)",
      description: "Calculates harness outer diameter (OD) and ensures bend curvature exceeds minimum ratio.",
      parameter: "Min Shielded Ratio: 6.0x OD",
      active: true,
    },
    {
      id: "RULE-COLOR-003",
      standardId: "ul-508a",
      name: "AC / DC Conductor Color Identification",
      severity: "MINOR",
      clause: "Table 28.1 (Field & Factory Wiring Colors)",
      description: "Enforces continuous White/Light Blue for AC neutral and Red/Black for DC positive/negative lines.",
      parameter: "Strict Color Palettes: Active",
      active: true,
    },
    {
      id: "RULE-TERM-004",
      standardId: "ul-508a",
      name: "Terminal Lug Torque Annotations",
      severity: "MINOR",
      clause: "§29.3 (Torque Markings)",
      description: "Checks that all terminal block screws and busbar bolts feature explicit torque callouts.",
      parameter: "Torque Units: N·m or in-lb required",
      active: true,
    },
    {
      id: "RULE-MIL-001",
      standardId: "mil-std-681D",
      name: "Military Lead Wire Color Banding",
      severity: "MINOR",
      clause: "Notice 2 §4.1 (Banded Coding)",
      description: "Validates 3-band numerical wire color coding against MIL-W-22759 specifications.",
      parameter: "Max Stripes: 3 Bands",
      active: true,
    },
    {
      id: "RULE-REV-005",
      standardId: "ipc-whma-a-620d",
      name: "Reference Designator Standard Prefix",
      severity: "INFO",
      clause: "MIL-STD-12D & IEEE 315 §22.2",
      description: "Checks schematic component prefixes against aerospace standards (e.g. K for relays, CB for breakers).",
      parameter: "Prefix Dictionary: Aerospace v2",
      active: true,
    },
  ];

  const toggleStandardActive = (id: string) => {
    setStandards((prev) =>
      prev.map((s) => (s.id === id ? { ...s, active: !s.active } : s))
    );
  };

  const filteredRules = rules.filter((r) => {
    const matchesStd = activeStandardId === "all" || r.standardId === activeStandardId;
    const matchesSearch =
      searchQuery.trim() === "" ||
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.clause.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStd && matchesSearch;
  });

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <div>
        <div className="flex items-center space-x-2 text-cyan-400 text-xs font-bold uppercase tracking-wider">
          <ShieldCheck className="h-4 w-4" />
          <span>Rule Matrix & Compliance Configuration</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
          Industry Standards & Deterministic Rules
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Configure rule sensitivities, tolerances, and acceptance thresholds enforced by the AI QC engine.
        </p>
      </div>

      {/* Standards Selector Pills */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {standards.map((std) => {
          const isSelected = activeStandardId === std.id;
          return (
            <div
              key={std.id}
              onClick={() => setActiveStandardId(std.id)}
              className={`p-4 rounded-xl border cursor-pointer transition-all ${
                isSelected
                  ? "border-cyan-500/50 bg-cyan-500/10 shadow-lg shadow-cyan-500/10"
                  : "border-white/10 bg-slate-900/40 hover:border-white/20"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-white">{std.code}</span>
                <input
                  type="checkbox"
                  checked={std.active}
                  onChange={(e) => {
                    e.stopPropagation();
                    toggleStandardActive(std.id);
                  }}
                  className="rounded border-slate-700 bg-slate-800 text-cyan-500"
                />
              </div>
              <div className="text-xs text-slate-400 mt-1 line-clamp-1">{std.name}</div>
              <div className="mt-3 flex items-center justify-between text-[11px]">
                <span className="text-cyan-400 font-mono">{std.ruleCount} Rules</span>
                <span className="text-slate-400">{std.category}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Rules Table */}
      <div className="glass-panel overflow-hidden space-y-4 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Enforced Compliance Rules
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Showing active deterministic validation rules for selected standards
            </p>
          </div>

          <div className="relative w-72">
            <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search rule ID, clause, or keywords..."
              className="w-full bg-slate-900 border border-white/10 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
            />
          </div>
        </div>

        <div className="divide-y divide-white/5 pt-2">
          {filteredRules.map((rule) => {
            const isCritical = rule.severity === "CRITICAL";
            const isMajor = rule.severity === "MAJOR";
            return (
              <div key={rule.id} className="py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-white">{rule.id}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                        isCritical
                          ? "bg-rose-500/10 text-rose-400 border-rose-500/30"
                          : isMajor
                          ? "bg-orange-500/10 text-orange-400 border-orange-500/30"
                          : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                      }`}
                    >
                      {rule.severity}
                    </span>
                    <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-500/20">
                      {rule.clause}
                    </span>
                  </div>
                  <h4 className="text-xs font-semibold text-slate-200">{rule.name}</h4>
                  <p className="text-xs text-slate-400">{rule.description}</p>
                </div>

                <div className="flex items-center space-x-4 shrink-0">
                  <div className="text-right text-[11px]">
                    <div className="text-slate-400 font-mono flex items-center space-x-1">
                      <Sliders className="h-3 w-3 text-cyan-400" />
                      <span>{rule.parameter}</span>
                    </div>
                    <span className="text-emerald-400 font-medium flex items-center justify-end space-x-1 mt-0.5">
                      <CheckCircle2 className="h-3 w-3" />
                      <span>Zero-False-Positive Verified</span>
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
