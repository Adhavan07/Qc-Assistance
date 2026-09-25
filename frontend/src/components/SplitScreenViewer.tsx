"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Download,
  FileSpreadsheet,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Search,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  Sparkles,
  ExternalLink,
  Layers,
} from "lucide-react";
import { QCFinding, QCRun, Severity } from "../types";
import { MOCK_QC_RUN } from "../lib/mockData";

interface SplitScreenViewerProps {
  runId?: string;
  onBackToDashboard?: () => void;
}

export default function SplitScreenViewer({ onBackToDashboard }: SplitScreenViewerProps) {
  const [qcRun] = useState<QCRun>(MOCK_QC_RUN);
  const [findings, setFindings] = useState<QCFinding[]>(MOCK_QC_RUN.findings);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>("f-01");
  const [hoveredFindingId, setHoveredFindingId] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activePage, setActivePage] = useState<number>(1);
  const [reportModalOpen, setReportModalOpen] = useState<boolean>(false);
  const [modalType, setModalType] = useState<"PDF" | "XLSX">("PDF");

  // Canvas Pan & Zoom State
  const [scale, setScale] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const [startPan, setStartPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const canvasRef = useRef<HTMLDivElement>(null);
  const cardsContainerRef = useRef<HTMLDivElement>(null);

  // Filter findings
  const filteredFindings = findings.filter((f) => {
    const matchesSeverity = severityFilter === "ALL" || f.severity === severityFilter;
    const matchesSearch =
      searchQuery.trim() === "" ||
      f.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.rule_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.standard_citation.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.evidence_text.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSeverity && matchesSearch;
  });

  // Handle Finding Feedback
  const handleFeedback = (findingId: string, status: "CORRECT" | "INCORRECT" | "NEEDS_REVIEW") => {
    setFindings((prev) =>
      prev.map((f) => {
        if (f.id === findingId) {
          return { ...f, feedback_status: status };
        }
        return f;
      })
    );
  };

  // Zoom Helpers
  const handleZoomIn = () => setScale((s) => Math.min(s + 0.2, 2.8));
  const handleZoomOut = () => setScale((s) => Math.max(s - 0.2, 0.5));
  const handleResetZoom = () => {
    setScale(1);
    setPan({ x: 0, y: 0 });
  };

  // Pan Handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // only left click
    setIsPanning(true);
    setStartPan({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isPanning) return;
    setPan({
      x: e.clientX - startPan.x,
      y: e.clientY - startPan.y,
    });
  };

  const handleMouseUp = () => {
    setIsPanning(false);
  };

  // Scroll finding card into view when clicked on canvas
  const selectFinding = (id: string) => {
    setSelectedFindingId(id);
    const cardEl = document.getElementById(`finding-card-${id}`);
    if (cardEl) {
      cardEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  };

  // Auto center on selected finding
  useEffect(() => {
    if (selectedFindingId) {
      const finding = findings.find((f) => f.id === selectedFindingId);
      if (finding && finding.location_bbox) {
        // Pan smoothly toward bbox center
        const bbox = finding.location_bbox;
        const centerX = -(bbox.x + bbox.width / 2 - 450);
        const centerY = -(bbox.y + bbox.height / 2 - 280);
        setPan({ x: Math.max(Math.min(centerX, 200), -200), y: Math.max(Math.min(centerY, 150), -150) });
      }
    }
  }, [selectedFindingId, findings]);

  const getSeverityColor = (sev: Severity) => {
    switch (sev) {
      case "CRITICAL":
        return { border: "#ef4444", fill: "rgba(239, 68, 68, 0.18)", text: "text-rose-400", badge: "bg-rose-500/10 border-rose-500/30 text-rose-400" };
      case "MAJOR":
        return { border: "#f97316", fill: "rgba(249, 115, 22, 0.18)", text: "text-orange-400", badge: "bg-orange-500/10 border-orange-500/30 text-orange-400" };
      case "MINOR":
        return { border: "#eab308", fill: "rgba(234, 179, 8, 0.18)", text: "text-amber-400", badge: "bg-amber-500/10 border-amber-500/30 text-amber-400" };
      case "INFO":
        return { border: "#38bdf8", fill: "rgba(56, 189, 248, 0.18)", text: "text-sky-400", badge: "bg-sky-500/10 border-sky-500/30 text-sky-400" };
    }
  };

  const getSeverityIcon = (sev: Severity) => {
    switch (sev) {
      case "CRITICAL":
        return <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />;
      case "MAJOR":
        return <AlertTriangle className="h-4 w-4 text-orange-400 shrink-0" />;
      case "MINOR":
        return <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />;
      case "INFO":
        return <Info className="h-4 w-4 text-sky-400 shrink-0" />;
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] overflow-hidden bg-[#080c14]">
      {/* Top Toolbar */}
      <div className="h-14 border-b border-white/10 px-6 flex items-center justify-between bg-slate-950/80 backdrop-blur shrink-0">
        <div className="flex items-center space-x-4">
          {onBackToDashboard && (
            <button
              onClick={onBackToDashboard}
              className="flex items-center space-x-1 text-xs text-slate-400 hover:text-white transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
              <span>Back</span>
            </button>
          )}

          <div className="flex items-center space-x-3">
            <h2 className="text-sm font-bold text-white tracking-tight">
              {qcRun.document_name}
            </h2>
            <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-rose-500/10 text-rose-400 border border-rose-500/30 font-bold uppercase">
              {qcRun.overall_status} (4 DEFECTS)
            </span>
            <span className="text-xs text-slate-500 hidden md:inline">
              Sheet {activePage} of 3 • IPC-WHMA-A-620D Class 3
            </span>
          </div>
        </div>

        {/* Action Buttons: PDF Report & Excel XLSX */}
        <div className="flex items-center space-x-2">
          {/* Sheet Selector */}
          <div className="flex items-center space-x-1 bg-slate-900 border border-white/10 rounded-lg px-2 py-1 text-xs text-slate-300">
            <button
              onClick={() => setActivePage((p) => Math.max(p - 1, 1))}
              disabled={activePage === 1}
              className="hover:text-white disabled:opacity-30"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <span className="font-mono text-[11px] px-1">Page {activePage} / 3</span>
            <button
              onClick={() => setActivePage((p) => Math.min(p + 1, 3))}
              disabled={activePage === 3}
              className="hover:text-white disabled:opacity-30"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>

          <button
            onClick={() => {
              setModalType("PDF");
              setReportModalOpen(true);
            }}
            id="download-pdf-report-btn"
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 text-slate-200 text-xs font-semibold transition-all hover:scale-[1.02]"
          >
            <Download className="h-3.5 w-3.5 text-cyan-400" />
            <span>Download PDF</span>
          </button>

          <button
            onClick={() => {
              setModalType("XLSX");
              setReportModalOpen(true);
            }}
            id="download-xlsx-report-btn"
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 text-slate-200 text-xs font-semibold transition-all hover:scale-[1.02]"
          >
            <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" />
            <span>Export Excel</span>
          </button>
        </div>
      </div>

      {/* Main Split Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT PANE (60%): Interactive Schematic Canvas */}
        <div className="w-[60%] relative flex flex-col border-r border-white/10 bg-[#070b12] overflow-hidden select-none">
          {/* Canvas Floating Controls */}
          <div className="absolute top-4 left-4 z-20 flex items-center space-x-1.5 rounded-xl border border-white/10 bg-slate-900/90 p-1 backdrop-blur shadow-2xl">
            <button
              onClick={handleZoomIn}
              className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="h-4 w-4" />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="h-4 w-4" />
            </button>
            <span className="font-mono text-[11px] text-slate-400 px-1.5">
              {Math.round(scale * 100)}%
            </span>
            <button
              onClick={handleResetZoom}
              className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
              title="Reset View"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
          </div>

          {/* Canvas Legend & Layer Indicator */}
          <div className="absolute bottom-4 left-4 z-20 flex items-center space-x-2 text-[10px] text-slate-400 rounded-lg bg-slate-900/90 border border-white/10 px-3 py-1.5 backdrop-blur">
            <Layers className="h-3.5 w-3.5 text-cyan-400" />
            <span>Overlays: 6 Bounding Boxes</span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-300">Drag to pan • Click box to inspect</span>
          </div>

          {/* Interactive Schematic Diagram Viewport */}
          <div
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            className={`w-full h-full flex items-center justify-center blueprint-grid cursor-grab ${
              isPanning ? "cursor-grabbing" : ""
            }`}
          >
            <div
              style={{
                transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
                transformOrigin: "center center",
                transition: isPanning ? "none" : "transform 0.15s cubic-bezier(0.4, 0, 0.2, 1)",
              }}
              className="relative w-[920px] h-[580px] bg-[#0c1424] rounded-lg shadow-2xl border border-white/10 overflow-hidden"
            >
              {/* Engineering Schematic Border & Title Block */}
              <div className="absolute inset-2 border border-slate-700/60 pointer-events-none">
                <div className="absolute top-2 left-3 text-[10px] font-mono text-cyan-500/70 uppercase">
                  BOEING 777X AVIONICS HARNESS • SYS-ELEC-401 • SHEET 01/03
                </div>
                <div className="absolute bottom-2 right-3 border border-slate-700/80 bg-slate-900/80 px-3 py-1.5 text-right font-mono text-[9px] text-slate-400">
                  <div className="text-white font-bold">SPANDSONS HORIZON ENGINEERING</div>
                  <div>REV D • CAGE CODE: 8X492 • SCALE: NTS</div>
                </div>
              </div>

              {/* Realistic SVG Wiring Diagram Circuit Content */}
              <svg className="w-full h-full" viewBox="0 0 920 580">
                <defs>
                  {/* Grid pattern */}
                  <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                    <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255,255,255,0.02)" strokeWidth="1" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#grid)" />

                {/* Circuit Breaker Group (Left) */}
                <g transform="translate(60, 100)">
                  <rect x="0" y="0" width="80" height="180" rx="4" fill="#131e36" stroke="#38bdf8" strokeWidth="1.5" />
                  <text x="40" y="24" fill="#94a3b8" fontSize="10" textAnchor="middle" fontWeight="bold">PANEL P1</text>
                  
                  {/* CB-101 */}
                  <rect x="15" y="40" width="50" height="30" rx="2" fill="#0f172a" stroke="#cbd5e1" strokeWidth="1" />
                  <text x="40" y="58" fill="#f8fafc" fontSize="9" textAnchor="middle" fontWeight="bold">CB-101</text>
                  <text x="40" y="80" fill="#38bdf8" fontSize="8" textAnchor="middle">20A</text>

                  {/* CB-102 */}
                  <rect x="15" y="95" width="50" height="30" rx="2" fill="#0f172a" stroke="#cbd5e1" strokeWidth="1" />
                  <text x="40" y="113" fill="#f8fafc" fontSize="9" textAnchor="middle" fontWeight="bold">CB-102</text>
                  <text x="40" y="135" fill="#38bdf8" fontSize="8" textAnchor="middle">15A</text>
                </g>

                {/* Wire Leads from Breakers */}
                {/* W101: CB-101 to J101 */}
                <path d="M 140 155 L 240 155 L 240 175 L 430 175" fill="none" stroke="#38bdf8" strokeWidth="2" strokeDasharray="none" />
                <text x="250" y="170" fill="#94a3b8" fontSize="9" fontFamily="monospace">W101 [16AWG / WHT]</text>

                {/* W102 (VIOLATION: MISSING GAUGE) */}
                <path d="M 140 230 L 320 230 L 320 205 L 430 205" fill="none" stroke="#ef4444" strokeWidth="2.5" />
                <text x="180" y="222" fill="#ef4444" fontSize="9" fontWeight="bold" fontFamily="monospace">
                  W102 [BLK - NO GAUGE]
                </text>

                {/* Connector J101 (Center) */}
                <g transform="translate(430, 140)">
                  <rect x="0" y="0" width="60" height="110" rx="4" fill="#1e293b" stroke="#38bdf8" strokeWidth="1.5" />
                  <text x="30" y="-8" fill="#38bdf8" fontSize="10" textAnchor="middle" fontWeight="bold">J101 RECEPTACLE</text>
                  
                  {/* Pin 1 */}
                  <circle cx="15" cy="35" r="4" fill="#38bdf8" />
                  <text x="25" y="38" fill="#e2e8f0" fontSize="8">P1</text>
                  
                  {/* Pin 2 */}
                  <circle cx="15" cy="65" r="4" fill="#ef4444" />
                  <text x="25" y="68" fill="#ef4444" fontSize="8">P2</text>

                  {/* Pin 4 (MISMATCH VIOLATION) */}
                  <circle cx="15" cy="90" r="4" fill="#f97316" />
                  <text x="25" y="93" fill="#f97316" fontSize="8" fontWeight="bold">P4 (20A)</text>
                </g>

                {/* Mating Plug P101 */}
                <g transform="translate(500, 140)">
                  <rect x="0" y="0" width="60" height="110" rx="4" fill="#1e293b" stroke="#cbd5e1" strokeWidth="1.5" strokeDasharray="3,2" />
                  <text x="30" y="-8" fill="#cbd5e1" fontSize="10" textAnchor="middle" fontWeight="bold">P101 PLUG</text>
                  
                  <circle cx="45" cy="35" r="4" fill="#38bdf8" />
                  <circle cx="45" cy="65" r="4" fill="#38bdf8" />
                  <circle cx="45" cy="90" r="4" fill="#f97316" />
                  <text x="22" y="93" fill="#f97316" fontSize="8" fontWeight="bold">P4 (16A)</text>
                </g>

                {/* Mating Pin 4 line */}
                <path d="M 445 230 L 545 230" fill="none" stroke="#f97316" strokeWidth="2.5" />

                {/* Relay Block K101 / RLY-1 (Upper Right) */}
                <g transform="translate(670, 150)">
                  <rect x="0" y="0" width="130" height="90" rx="4" fill="#131e36" stroke="#94a3b8" strokeWidth="1.5" />
                  <text x="65" y="22" fill="#f8fafc" fontSize="10" textAnchor="middle" fontWeight="bold">RLY-1</text>
                  <text x="65" y="38" fill="#38bdf8" fontSize="8" textAnchor="middle">28VDC AUX CONTACTOR</text>

                  <rect x="20" y="50" width="20" height="20" fill="#0f172a" stroke="#cbd5e1" />
                  <text x="30" y="64" fill="#cbd5e1" fontSize="8" textAnchor="middle">A1</text>

                  <rect x="90" y="50" width="20" height="20" fill="#0f172a" stroke="#cbd5e1" />
                  <text x="100" y="64" fill="#cbd5e1" fontSize="8" textAnchor="middle">A2</text>
                </g>

                {/* Terminal Busbar & Lug-T4 (Lower Right) */}
                <g transform="translate(660, 310)">
                  <rect x="0" y="0" width="160" height="80" rx="3" fill="#1e293b" stroke="#eab308" strokeWidth="1" />
                  <text x="80" y="20" fill="#eab308" fontSize="10" textAnchor="middle" fontWeight="bold">BUS-24V DC POWER</text>
                  
                  {/* Lug-T4 */}
                  <rect x="25" y="35" width="40" height="30" fill="#0f172a" stroke="#eab308" strokeWidth="1.5" />
                  <text x="45" y="53" fill="#f8fafc" fontSize="8" textAnchor="middle" fontWeight="bold">LUG-T4</text>
                  <text x="110" y="53" fill="#94a3b8" fontSize="8">NO TORQUE</text>
                </g>

                {/* Harness Bundle Bend Radius (Center Lower) */}
                <g transform="translate(340, 330)">
                  <path d="M 0 30 Q 70 80 120 40 T 190 20" fill="none" stroke="#f97316" strokeWidth="5" strokeLinecap="round" />
                  <text x="95" y="85" fill="#f97316" fontSize="9" fontWeight="bold">HV-BUNDLE-A (R12mm)</text>
                  <text x="95" y="98" fill="#94a3b8" fontSize="8">REQ: R48mm (6x OD)</text>
                </g>

                {/* Wire W204 Color Violation (Lower Left) */}
                <g transform="translate(120, 420)">
                  <path d="M 10 35 L 180 35" fill="none" stroke="#f97316" strokeWidth="3" />
                  <text x="20" y="28" fill="#f97316" fontSize="9" fontWeight="bold" fontFamily="monospace">
                    W204 [ORG] - AC NEUTRAL RETURN
                  </text>
                </g>

                {/* INTERACTIVE BOUNDING BOX OVERLAYS */}
                {findings.map((f) => {
                  if (!f.location_bbox) return null;
                  const bbox = f.location_bbox;
                  const isSelected = selectedFindingId === f.id;
                  const isHovered = hoveredFindingId === f.id;
                  const colors = getSeverityColor(f.severity);

                  return (
                    <g
                      key={f.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        selectFinding(f.id);
                      }}
                      onMouseEnter={() => setHoveredFindingId(f.id)}
                      onMouseLeave={() => setHoveredFindingId(null)}
                      className="cursor-pointer"
                    >
                      {/* Highlighted Bounding Box */}
                      <rect
                        x={bbox.x}
                        y={bbox.y}
                        width={bbox.width}
                        height={bbox.height}
                        rx="4"
                        fill={colors.fill}
                        stroke={colors.border}
                        strokeWidth={isSelected ? 3 : isHovered ? 2.5 : 1.8}
                        strokeDasharray={isSelected ? "none" : "4 2"}
                        className={`transition-all duration-150 ${
                          isSelected ? "drop-shadow-[0_0_8px_rgba(239,68,68,0.8)]" : ""
                        }`}
                      />

                      {/* Tag Pill with Finding Code */}
                      <rect
                        x={bbox.x}
                        y={bbox.y - 18}
                        width={84}
                        height={18}
                        rx="3"
                        fill={colors.border}
                      />
                      <text
                        x={bbox.x + 6}
                        y={bbox.y - 5}
                        fill="#ffffff"
                        fontSize="9"
                        fontWeight="bold"
                        fontFamily="monospace"
                      >
                        {f.finding_code}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>
        </div>

        {/* RIGHT PANE (40%): Discrepancy Drawer / Inspector */}
        <div className="w-[40%] flex flex-col bg-slate-950/70 border-l border-white/10 overflow-hidden">
          {/* Severity Filter Tabs & Search */}
          <div className="p-4 border-b border-white/10 space-y-3 bg-slate-950/90 shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <ShieldAlert className="h-4 w-4 text-cyan-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-white">
                  Inspection Findings ({filteredFindings.length})
                </h3>
              </div>
              <span className="text-[11px] text-slate-400">
                Sorted by Severity
              </span>
            </div>

            {/* Severity Pill Filter */}
            <div className="flex items-center space-x-1 overflow-x-auto pb-1">
              {[
                { id: "ALL", label: `All (${findings.length})` },
                { id: "CRITICAL", label: "Critical (1)", color: "text-rose-400" },
                { id: "MAJOR", label: "Major (2)", color: "text-orange-400" },
                { id: "MINOR", label: "Minor (2)", color: "text-amber-400" },
                { id: "INFO", label: "Info (1)", color: "text-sky-400" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setSeverityFilter(tab.id)}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all whitespace-nowrap ${
                    severityFilter === tab.id
                      ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                      : `bg-white/5 text-slate-400 hover:text-white border border-transparent ${tab.color || ""}`
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search rule, wire ID, connector, or citation..."
                className="w-full bg-slate-900 border border-white/10 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50"
              />
            </div>
          </div>

          {/* Scrollable Findings Cards List */}
          <div ref={cardsContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
            {filteredFindings.map((finding) => {
              const isSelected = selectedFindingId === finding.id;
              const isHovered = hoveredFindingId === finding.id;
              const colors = getSeverityColor(finding.severity);

              return (
                <div
                  key={finding.id}
                  id={`finding-card-${finding.id}`}
                  onClick={() => selectFinding(finding.id)}
                  onMouseEnter={() => setHoveredFindingId(finding.id)}
                  onMouseLeave={() => setHoveredFindingId(null)}
                  className={`rounded-xl border p-4 transition-all duration-200 cursor-pointer ${
                    isSelected
                      ? "bg-slate-900/90 border-cyan-500/60 shadow-xl shadow-cyan-500/10 scale-[1.01]"
                      : isHovered
                      ? "bg-slate-900/60 border-white/20"
                      : "bg-slate-900/40 border-white/10 hover:border-white/20"
                  }`}
                >
                  {/* Card Header: Severity & Finding Code */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {getSeverityIcon(finding.severity)}
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${colors.badge}`}>
                        {finding.severity}
                      </span>
                      <span className="font-mono text-xs font-semibold text-slate-300">
                        {finding.finding_code}
                      </span>
                    </div>
                    <span className="font-mono text-[10px] text-slate-400 bg-white/5 px-2 py-0.5 rounded">
                      {finding.rule_id}
                    </span>
                  </div>

                  {/* Finding Title & Description */}
                  <h4 className="text-xs font-bold text-white mt-2 leading-relaxed">
                    {finding.description}
                  </h4>

                  {/* Standard Citation */}
                  <div className="mt-2.5 flex items-start space-x-1.5 text-[11px] text-cyan-300 bg-cyan-950/40 border border-cyan-500/20 rounded-lg p-2 font-mono">
                    <Sparkles className="h-3.5 w-3.5 text-cyan-400 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-bold text-cyan-200">{finding.standard_citation}</div>
                      <div className="text-[10px] text-cyan-300/80 font-sans mt-0.5">
                        {finding.requirement_text}
                      </div>
                    </div>
                  </div>

                  {/* Extracted Diagram Evidence */}
                  <div className="mt-2 text-[11px] text-slate-400 bg-black/40 rounded-lg p-2 border border-white/5 font-mono">
                    <span className="text-slate-500">Evidence: </span>
                    <span className="text-slate-300">{finding.evidence_text}</span>
                  </div>

                  {/* Remedial Recommendation */}
                  <div className="mt-2 text-[11px] text-emerald-300 bg-emerald-950/30 border border-emerald-500/20 rounded-lg p-2">
                    <span className="font-bold text-emerald-400">Action: </span>
                    <span>{finding.recommendation}</span>
                  </div>

                  {/* Confidence Score Bar */}
                  <div className="mt-3 flex items-center justify-between text-[10px] text-slate-400 pt-2 border-t border-white/5">
                    <div className="flex items-center space-x-1.5">
                      <span>AI Confidence:</span>
                      <span className="font-mono font-bold text-slate-200">
                        {(finding.confidence_score * 100).toFixed(1)}% ({finding.confidence_level})
                      </span>
                    </div>

                    {/* Interactive Feedback Buttons */}
                    <div className="flex items-center space-x-1">
                      {finding.feedback_status ? (
                        <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase bg-white/10 text-cyan-300">
                          {finding.feedback_status}
                        </span>
                      ) : (
                        <>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleFeedback(finding.id, "CORRECT");
                            }}
                            title="Verify Finding"
                            className="p-1 rounded hover:bg-emerald-500/20 text-slate-400 hover:text-emerald-400 transition-colors"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleFeedback(finding.id, "INCORRECT");
                            }}
                            title="Flag False Alarm"
                            className="p-1 rounded hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition-colors"
                          >
                            <XCircle className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleFeedback(finding.id, "NEEDS_REVIEW");
                            }}
                            title="Flag for Human Review"
                            className="p-1 rounded hover:bg-amber-500/20 text-slate-400 hover:text-amber-400 transition-colors"
                          >
                            <HelpCircle className="h-3.5 w-3.5" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Export Report Modal */}
      {reportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="glass-panel p-6 max-w-md w-full border-cyan-500/40 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {modalType === "PDF" ? (
                  <Download className="h-5 w-5 text-cyan-400" />
                ) : (
                  <FileSpreadsheet className="h-5 w-5 text-emerald-400" />
                )}
                <h3 className="font-bold text-white text-sm">
                  Export Compliance {modalType === "PDF" ? "Report (PDF)" : "Matrix (Excel)"}
                </h3>
              </div>
              <button
                onClick={() => setReportModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-400">
              The AI Engine will compile complete findings, standards citations, bounding box annotations,
              and remedial actions into a formal compliance artifact.
            </p>

            <div className="rounded-lg bg-slate-900 p-3 text-xs font-mono space-y-1 text-slate-300">
              <div>Document: {qcRun.document_name}</div>
              <div>Standards: IPC-WHMA-A-620D, UL 508A</div>
              <div>Total Findings: {findings.length}</div>
              <div>Sign-off: Spandsons Horizon Engineering</div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2">
              <button
                onClick={() => setReportModalOpen(false)}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setReportModalOpen(false);
                  alert(`Downloading ${modalType} compliance report for ${qcRun.document_name}...`);
                }}
                className="px-4 py-2 rounded-lg text-xs font-bold text-white bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 shadow-md shadow-cyan-600/20"
              >
                Download Now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
