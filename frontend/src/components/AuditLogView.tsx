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
        <div className="flex items-center space-x-2 text-blue-600 text-xs font-bold uppercase tracking-wider">
          <FileCheck2 className="h-4 w-4" />
          <span>AS9100 / ISO 9001 Compliance Audit Trail</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
          Cryptographic Compliance Activity Logs
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Immutable event log tracking all schematic uploads, AI inspections, findings reviews, and report generation.
        </p>
      </div>

      <div className="pro-card overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Key className="h-4 w-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Tenant Event Stream
            </h3>
          </div>
          <span className="text-xs text-emerald-700 font-mono bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200 flex items-center space-x-1 font-semibold">
            <CheckCircle className="h-3.5 w-3.5 text-emerald-600" />
            <span>Audit Chain Verified</span>
          </span>
        </div>

        <div className="divide-y divide-slate-100 text-xs">
          {auditLogs.map((log) => (
            <div key={log.id} className="p-4 hover:bg-slate-50 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="font-mono font-bold text-blue-800 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                    {log.action}
                  </span>
                  <span className="text-slate-400">•</span>
                  <span className="font-semibold text-slate-900">{log.resource}</span>
                </div>
                <div className="text-slate-500 text-[11px]">{log.details}</div>
              </div>

              <div className="text-right text-[11px] text-slate-500 shrink-0 space-y-0.5">
                <div className="text-slate-800 font-semibold flex items-center justify-end space-x-1">
                  <User className="h-3.5 w-3.5 text-blue-600" />
                  <span>{log.actor}</span>
                </div>
                <div className="font-mono text-slate-400">{log.timestamp} • IP: {log.ip}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
