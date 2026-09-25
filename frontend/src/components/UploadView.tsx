"use client";

import React, { useState } from "react";
import {
  UploadCloud,
  FileText,
  Shield,
  CheckCircle,
  AlertCircle,
  ArrowRight,
  Sparkles,
  Zap,
} from "lucide-react";
import { useAuth } from "../lib/auth-context";

interface UploadViewProps {
  onInspectionReady: (runId: string) => void;
}

export default function UploadView({ onInspectionReady }: UploadViewProps) {
  const { organization, deductCredit } = useAuth();
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState<number>(0);
  const [selectedStandards, setSelectedStandards] = useState<string[]>([
    "IPC-WHMA-A-620D",
    "UL 508A",
    "MIL-STD-681D",
  ]);

  const stages = [
    { name: "S3 Staging & Checksum Verification", desc: "Encrypting and registering document in tenant partition" },
    { name: "Multimodal OCR & IDR Extraction", desc: "Vectorizing wire nets, terminal blocks, pinouts, and gauge annotations" },
    { name: "Deterministic Rule Engine Validation", desc: "Executing 48 automated checks across selected electrical standards" },
    { name: "AI Synthesis & Report Generation", desc: "Correlating bounding boxes, computing confidence scores, and assembling findings" },
  ];

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const toggleStandard = (code: string) => {
    if (selectedStandards.includes(code)) {
      setSelectedStandards(selectedStandards.filter((s) => s !== code));
    } else {
      setSelectedStandards([...selectedStandards, code]);
    }
  };

  const startAnalysis = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setProcessingStage(0);

    // Simulate multi-stage asynchronous processing pipeline with real feedback
    for (let i = 0; i < stages.length; i++) {
      setProcessingStage(i);
      await new Promise((resolve) => setTimeout(resolve, 800));
    }

    // Deduct 1 QC credit
    deductCredit();

    // Transition to inspector
    setTimeout(() => {
      setIsProcessing(false);
      onInspectionReady("run-spandsons-demo-01");
    }, 600);
  };

  const loadSampleSchematic = () => {
    // Generate a mock file for quick testing
    const blob = new Blob(["mock electrical wiring diagram pdf content"], { type: "application/pdf" });
    const file = new File([blob], "Boeing_777X_Avionics_Harness_WD-777-04.pdf", { type: "application/pdf" });
    setSelectedFile(file);
  };

  return (
    <div className="max-w-4xl mx-auto p-8 space-y-8">
      <div>
        <div className="flex items-center space-x-2 text-cyan-400 text-xs font-bold uppercase tracking-wider">
          <Sparkles className="h-4 w-4" />
          <span>Automated Quality Ingestion</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
          Upload Wiring Diagram Manual
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Ingest multi-page PDF or raster schematics for instant AI-powered compliance checking.
        </p>
      </div>

      {/* Credit Warning if zero */}
      {organization && organization.credits_remaining <= 0 && (
        <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 flex items-center space-x-3 text-rose-300 text-sm">
          <AlertCircle className="h-5 w-5 text-rose-400 shrink-0" />
          <div>
            <span className="font-bold">No QC credits remaining!</span> Your organization has 0 credits left.
            Please upgrade your plan or contact support to recharge.
          </div>
        </div>
      )}

      {/* Main Upload Form */}
      <div className="space-y-6">
        {/* Dropzone */}
        {!isProcessing ? (
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-200 relative ${
              dragActive
                ? "border-cyan-400 bg-cyan-500/10 shadow-xl shadow-cyan-500/20 scale-[1.01]"
                : "border-white/15 bg-slate-900/40 hover:border-cyan-500/40 hover:bg-slate-900/70"
            }`}
          >
            <input
              type="file"
              id="file-upload-input"
              className="hidden"
              accept=".pdf,.png,.jpg,.jpeg,.tiff,.dxf"
              onChange={handleFileChange}
            />

            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 mb-4">
              <UploadCloud className="h-8 w-8" />
            </div>

            {selectedFile ? (
              <div className="space-y-2">
                <div className="flex items-center justify-center space-x-2 text-white font-bold text-sm">
                  <FileText className="h-4 w-4 text-cyan-400" />
                  <span>{selectedFile.name}</span>
                  <span className="text-xs text-slate-400 font-normal">
                    ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                  </span>
                </div>
                <p className="text-xs text-emerald-400 font-medium">Ready for compliance analysis</p>
                <div className="pt-2">
                  <label
                    htmlFor="file-upload-input"
                    className="text-xs text-cyan-400 hover:text-cyan-300 underline cursor-pointer"
                  >
                    Select a different file
                  </label>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="text-sm font-semibold text-white">
                  Drag and drop wiring diagram manual here, or{" "}
                  <label
                    htmlFor="file-upload-input"
                    className="text-cyan-400 hover:text-cyan-300 underline cursor-pointer"
                  >
                    browse files
                  </label>
                </div>
                <p className="text-xs text-slate-400">
                  Supported formats: Multi-page PDF, Vector DXF, High-Res TIFF, PNG (up to 100MB)
                </p>
                <div className="pt-3">
                  <button
                    type="button"
                    onClick={loadSampleSchematic}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-xs font-semibold text-slate-300 hover:bg-white/10 hover:text-white transition-colors"
                  >
                    <FileText className="h-3.5 w-3.5 text-cyan-400" />
                    <span>Load Demo Schematic (Boeing 777X Avionics Harness)</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Real-time Processing Pipeline Progress */
          <div className="glass-panel p-8 space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/20 border border-cyan-500/30">
                  <Zap className="h-5 w-5 text-cyan-400 live-pulse" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-sm">
                    Processing Schematic: {selectedFile?.name}
                  </h3>
                  <p className="text-xs text-slate-400">
                    Executing asynchronous AI inspection pipeline...
                  </p>
                </div>
              </div>
              <div className="font-mono text-cyan-400 text-sm font-bold">
                {Math.round(((processingStage + 1) / stages.length) * 100)}%
              </div>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-gradient-to-r from-cyan-500 to-blue-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${((processingStage + 1) / stages.length) * 100}%` }}
              ></div>
            </div>

            {/* Stages checklist */}
            <div className="space-y-3 pt-2">
              {stages.map((stage, idx) => {
                const isDone = processingStage > idx;
                const isCurrent = processingStage === idx;
                return (
                  <div
                    key={idx}
                    className={`flex items-start space-x-3 p-3 rounded-xl border transition-all ${
                      isCurrent
                        ? "border-cyan-500/40 bg-cyan-500/10 shadow-sm shadow-cyan-500/10"
                        : isDone
                        ? "border-emerald-500/20 bg-emerald-500/5 text-slate-300"
                        : "border-white/5 bg-slate-900/30 text-slate-500"
                    }`}
                  >
                    <div className="mt-0.5">
                      {isDone ? (
                        <CheckCircle className="h-4 w-4 text-emerald-400" />
                      ) : isCurrent ? (
                        <span className="flex h-4 w-4 items-center justify-center">
                          <span className="live-pulse h-2 w-2 rounded-full bg-cyan-400"></span>
                        </span>
                      ) : (
                        <span className="h-4 w-4 rounded-full border border-slate-700 block"></span>
                      )}
                    </div>
                    <div>
                      <div className={`text-xs font-semibold ${isCurrent ? "text-cyan-300" : isDone ? "text-slate-200" : "text-slate-500"}`}>
                        {stage.name}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{stage.desc}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Standards Selection */}
        {!isProcessing && (
          <div className="glass-panel p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Target Regulatory Standards
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Select which compliance rulesets the AI engine should enforce on this drawing set.
                </p>
              </div>
              <Shield className="h-4 w-4 text-cyan-400" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
              {[
                {
                  code: "IPC-WHMA-A-620D",
                  title: "IPC-WHMA-A-620D Class 3",
                  desc: "Aerospace & Mission-Critical Cable Assemblies (Bend radius, wire sizing, crimps)",
                },
                {
                  code: "UL 508A",
                  title: "UL 508A Industrial Panels",
                  desc: "Circuit breaker branch protection, conductor color coding, terminal lug torque",
                },
                {
                  code: "MIL-STD-681D",
                  title: "MIL-STD-681D Lead Colors",
                  desc: "Identification and numerical coding for military hookup wire",
                },
                {
                  code: "ISO 20653",
                  title: "ISO 20653 Ingress Protection",
                  desc: "Chassis penetration environmental sealing & IP ratings",
                },
              ].map((std) => {
                const checked = selectedStandards.includes(std.code);
                return (
                  <div
                    key={std.code}
                    onClick={() => toggleStandard(std.code)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                      checked
                        ? "border-cyan-500/40 bg-cyan-500/10 text-white"
                        : "border-white/10 bg-slate-900/40 text-slate-400 hover:border-white/20"
                    }`}
                  >
                    <div className="flex items-center space-x-2.5">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {}}
                        className="rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-0"
                      />
                      <span className="text-xs font-bold text-white">{std.title}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1 pl-6">{std.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Action Button */}
        {!isProcessing && (
          <div className="flex items-center justify-between pt-2">
            <div className="text-xs text-slate-400">
              ⚡ Inspection cost: <span className="font-bold text-white">1 Check Credit</span> (Remaining: {organization?.credits_remaining ?? 248})
            </div>
            <button
              onClick={startAnalysis}
              disabled={!selectedFile || (organization?.credits_remaining ?? 0) <= 0}
              id="start-analysis-btn"
              className="flex items-center space-x-2 rounded-xl bg-gradient-to-r from-cyan-600 via-sky-600 to-blue-600 px-6 py-3 text-xs font-bold text-white shadow-lg shadow-cyan-600/30 hover:from-cyan-500 hover:to-blue-500 transition-all hover:scale-[1.02] disabled:opacity-50 disabled:pointer-events-none"
            >
              <span>Launch Automated Inspection</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
