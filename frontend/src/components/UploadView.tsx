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

    for (let i = 0; i < stages.length; i++) {
      setProcessingStage(i);
      await new Promise((resolve) => setTimeout(resolve, 800));
    }

    deductCredit();

    setTimeout(() => {
      setIsProcessing(false);
      onInspectionReady("run-spandsons-demo-01");
    }, 600);
  };

  const loadSampleSchematic = () => {
    const blob = new Blob(["mock electrical wiring diagram pdf content"], { type: "application/pdf" });
    const file = new File([blob], "Boeing_777X_Avionics_Harness_WD-777-04.pdf", { type: "application/pdf" });
    setSelectedFile(file);
  };

  return (
    <div className="max-w-4xl mx-auto p-8 space-y-8">
      <div>
        <div className="flex items-center space-x-2 text-blue-600 text-xs font-bold uppercase tracking-wider">
          <Sparkles className="h-4 w-4" />
          <span>Automated Quality Ingestion</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
          Upload Wiring Diagram Manual
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Ingest multi-page PDF or raster schematics for instant AI-powered compliance checking.
        </p>
      </div>

      {/* Credit Warning if zero */}
      {organization && organization.credits_remaining <= 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 flex items-center space-x-3 text-red-800 text-sm">
          <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
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
                ? "border-blue-600 bg-blue-50/60 shadow-md scale-[1.01]"
                : "border-slate-300 bg-white hover:border-blue-500 hover:bg-slate-50/50"
            }`}
          >
            <input
              type="file"
              id="file-upload-input"
              className="hidden"
              accept=".pdf,.png,.jpg,.jpeg,.tiff,.dxf"
              onChange={handleFileChange}
            />

            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 border border-blue-100 text-blue-600 mb-4">
              <UploadCloud className="h-8 w-8" />
            </div>

            {selectedFile ? (
              <div className="space-y-2">
                <div className="flex items-center justify-center space-x-2 text-slate-900 font-bold text-sm">
                  <FileText className="h-4 w-4 text-blue-600" />
                  <span>{selectedFile.name}</span>
                  <span className="text-xs text-slate-500 font-normal">
                    ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                  </span>
                </div>
                <p className="text-xs text-emerald-600 font-semibold">Ready for compliance analysis</p>
                <div className="pt-2">
                  <label
                    htmlFor="file-upload-input"
                    className="text-xs text-blue-600 hover:text-blue-800 underline cursor-pointer font-medium"
                  >
                    Select a different file
                  </label>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="text-sm font-semibold text-slate-800">
                  Drag and drop wiring diagram manual here, or{" "}
                  <label
                    htmlFor="file-upload-input"
                    className="text-blue-600 hover:text-blue-800 underline cursor-pointer font-bold"
                  >
                    browse files
                  </label>
                </div>
                <p className="text-xs text-slate-500">
                  Supported formats: Multi-page PDF, Vector DXF, High-Res TIFF, PNG (up to 100MB)
                </p>
                <div className="pt-3">
                  <button
                    type="button"
                    onClick={loadSampleSchematic}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-200 hover:text-slate-900 transition-colors cursor-pointer"
                  >
                    <FileText className="h-3.5 w-3.5 text-blue-600" />
                    <span>Load Demo Schematic (Boeing 777X Avionics Harness)</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Real-time Processing Pipeline Progress */
          <div className="pro-card p-8 space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 border border-blue-200">
                  <Zap className="h-5 w-5 text-blue-600 live-pulse" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">
                    Processing Schematic: {selectedFile?.name}
                  </h3>
                  <p className="text-xs text-slate-500">
                    Executing asynchronous AI inspection pipeline...
                  </p>
                </div>
              </div>
              <div className="font-mono text-blue-600 text-sm font-bold">
                {Math.round(((processingStage + 1) / stages.length) * 100)}%
              </div>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
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
                    className={`flex items-start space-x-3 p-3.5 rounded-xl border transition-all ${
                      isCurrent
                        ? "border-blue-300 bg-blue-50/60 shadow-xs"
                        : isDone
                        ? "border-emerald-200 bg-emerald-50/50 text-slate-800"
                        : "border-slate-200 bg-slate-50/40 text-slate-400"
                    }`}
                  >
                    <div className="mt-0.5">
                      {isDone ? (
                        <CheckCircle className="h-4 w-4 text-emerald-600" />
                      ) : isCurrent ? (
                        <span className="flex h-4 w-4 items-center justify-center">
                          <span className="live-pulse h-2.5 w-2.5 rounded-full bg-blue-600"></span>
                        </span>
                      ) : (
                        <span className="h-4 w-4 rounded-full border border-slate-300 block"></span>
                      )}
                    </div>
                    <div>
                      <div className={`text-xs font-bold ${isCurrent ? "text-blue-900" : isDone ? "text-slate-800" : "text-slate-500"}`}>
                        {stage.name}
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">{stage.desc}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Standards Selection */}
        {!isProcessing && (
          <div className="pro-card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                  Target Regulatory Standards
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Select which compliance rulesets the AI engine should enforce on this drawing set.
                </p>
              </div>
              <Shield className="h-4 w-4 text-blue-600" />
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
                        ? "border-blue-400 bg-blue-50/50 shadow-xs"
                        : "border-slate-200 bg-white hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-center space-x-2.5">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {}}
                        className="rounded border-slate-300 text-blue-600 focus:ring-0 cursor-pointer"
                      />
                      <span className="text-xs font-bold text-slate-900">{std.title}</span>
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1 pl-6 leading-relaxed">{std.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Action Button */}
        {!isProcessing && (
          <div className="flex items-center justify-between pt-2">
            <div className="text-xs text-slate-600">
              ⚡ Inspection cost: <span className="font-bold text-slate-900">1 Check Credit</span> (Remaining: {organization?.credits_remaining ?? 248})
            </div>
            <button
              onClick={startAnalysis}
              disabled={!selectedFile || (organization?.credits_remaining ?? 0) <= 0}
              id="start-analysis-btn"
              className="flex items-center space-x-2 rounded-xl bg-blue-600 px-6 py-3 text-xs font-bold text-white shadow-sm hover:bg-blue-700 transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
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
