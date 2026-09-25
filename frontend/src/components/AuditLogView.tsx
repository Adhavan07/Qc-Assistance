"use client";

import React from "react";
import { FileCheck2, User, Key, CheckCircle } from "lucide-react";

export default function AuditLogView() {
  const auditLogs = [
    {
      id: "aud-01",
      action: "QC_RUN_EXECUTED",
      actor: "Gogulnath (Lead QA Engineer)",
      resource: "Boeing_777X_Avionics_Harness_WD-777-04.pdf",
      timestamp: "Today, 17:42:10",
      ip: "103.21.244.18",
      status: "COMPLETED",
      details: "48 checks executed, 4 violations detected, 1 credit deducted",
    },
    {
      id: "aud-02",
      action: "FINDING_FEEDBACK_SUBMITTED",
      actor: "Gogulnath (Lead QA Engineer)",
      resource: "FIND-001 (RULE-WIRE-001)",
      timestamp: "Today, 17:44:02",
      ip: "103.21.244.18",
      status: "VERIFIED",
      details: "Finding marked CORRECT by inspector. Model weights adjusted.",
    },
    {
      id: "aud-03",
      action: "DOCUMENT_UPLOADED",
      actor: "Pravin (Admin)",
      resource: "ABB_Series_400_Motor_Control_Panel_Sch.pdf",
      timestamp: "Yesterday, 14:15:32",
      ip: "103.21.244.22",
      status: "SUCCESS",
      details: "SHA-256: 7f8a92b... Presigned S3 staging confirmed",
    },
    {
      id: "aud-04",
      action: "REPORT_EXPORTED_PDF",
      actor: "Pravin (Admin)",
      resource: "Honeywell_APU_Controller_Wiring_Rev3.pdf",
      timestamp: "2 days ago",
      ip: "103.21.244.22",
      status: "DOWNLOADED",
      details: "AS9100 formal verification certificate generated",
    },
    {
      id: "aud-05",
      action: "ORGANIZATION_CREDITS_PURCHASED",
      actor: "Pravin (Admin)",
      resource: "Plan: ENTERPRISE",
      timestamp: "5 days ago",
      ip: "103.21.244.22",
      status: "CONFIRMED",
      details: "Added 250 automated QC inspection credits",
    },
  ];

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <div>
        <div className="flex items-center space-x-2 text-cyan-400 text-xs font-bold uppercase tracking-wider">
          <FileCheck2 className="h-4 w-4" />
          <span>AS9100 / ISO 9001 Compliance Audit Trail</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white mt-1">
          Cryptographic Compliance Activity Logs
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Immutable event log tracking all schematic uploads, AI inspections, findings reviews, and report generation.
        </p>
      </div>

      <div className="glass-panel overflow-hidden">
        <div className="p-5 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Key className="h-4 w-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Tenant Event Stream
            </h3>
          </div>
          <span className="text-xs text-emerald-400 font-mono bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20 flex items-center space-x-1">
            <CheckCircle className="h-3 w-3" />
            <span>Audit Chain Verified</span>
          </span>
        </div>

        <div className="divide-y divide-white/5 text-xs">
          {auditLogs.map((log) => (
            <div key={log.id} className="p-4 hover:bg-white/5 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="font-mono font-bold text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-500/20">
                    {log.action}
                  </span>
                  <span className="text-slate-400">•</span>
                  <span className="font-medium text-white">{log.resource}</span>
                </div>
                <div className="text-slate-400 text-[11px]">{log.details}</div>
              </div>

              <div className="text-right text-[11px] text-slate-400 shrink-0 space-y-0.5">
                <div className="text-slate-300 font-medium flex items-center justify-end space-x-1">
                  <User className="h-3 w-3 text-cyan-400" />
                  <span>{log.actor}</span>
                </div>
                <div className="font-mono text-slate-500">{log.timestamp} • IP: {log.ip}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
