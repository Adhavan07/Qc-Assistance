"use client";

import React from "react";
import { Cpu, Zap, Shield, Sparkles, UserCheck } from "lucide-react";
import { useAuth } from "../lib/auth-context";

interface NavbarProps {
  onUploadClick: () => void;
}

export default function Navbar({ onUploadClick }: NavbarProps) {
  const { user, organization } = useAuth();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 bg-white shadow-xs">
      <div className="flex h-16 items-center justify-between px-6">
        {/* Left: Brand & Engineering Workspace Indicator */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 shadow-sm text-white">
              <Cpu className="h-5 w-5 text-white" />
              <span className="absolute -bottom-0.5 -right-0.5 flex h-2.5 w-2.5">
                <span className="live-pulse absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500 border-2 border-white"></span>
              </span>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold tracking-tight text-slate-900 text-base">
                  Wiring Diagram QC
                </span>
                <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold tracking-wider text-blue-700 border border-blue-200 uppercase">
                  Enterprise
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">
                {organization?.name || "Spandsons Horizon Engineering Pvt. Ltd."}
              </p>
            </div>
          </div>

          <div className="hidden lg:flex items-center space-x-2 pl-4 border-l border-slate-200">
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs text-slate-700">
              <Shield className="h-3.5 w-3.5 text-blue-600" />
              <span className="font-mono text-[11px] font-medium text-slate-800">IPC-WHMA-A-620D Cl.3</span>
            </div>
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs text-slate-700">
              <span className="font-mono text-[11px] font-medium text-amber-800">UL 508A</span>
            </div>
          </div>
        </div>

        {/* Center: System Operational Status */}
        <div className="hidden md:flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-xs text-emerald-800">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="font-semibold">Hybrid AI QC Engine v1.0 Online</span>
          <span className="text-emerald-700/70 font-mono text-[11px]">• Latency: 1.8s</span>
        </div>

        {/* Right: Credits, New Inspection CTA & User Profile */}
        <div className="flex items-center space-x-3">
          {/* Credit Meter */}
          <div className="flex items-center space-x-2 bg-amber-50/80 border border-amber-200 rounded-lg px-3 py-1.5">
            <Zap className="h-4 w-4 text-amber-600 fill-amber-500" />
            <div className="text-right">
              <div className="text-xs font-bold text-amber-950">
                {organization?.credits_remaining ?? 248} <span className="font-normal text-amber-800/80">credits</span>
              </div>
              <div className="text-[10px] text-amber-700 font-mono uppercase tracking-wider font-semibold">
                {organization?.plan_tier || "Enterprise"} Plan
              </div>
            </div>
          </div>

          {/* Quick Upload CTA */}
          <button
            onClick={onUploadClick}
            id="nav-quick-upload-btn"
            className="flex items-center space-x-2 rounded-lg bg-blue-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition-all hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
          >
            <Sparkles className="h-4 w-4" />
            <span>New Inspection</span>
          </button>

          {/* User Profile */}
          <div className="flex items-center space-x-2.5 pl-2 border-l border-slate-200">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 border border-slate-200 text-sm font-bold text-blue-700">
              {user?.full_name ? user.full_name[0] : "G"}
            </div>
            <div className="hidden xl:block text-left text-xs">
              <div className="font-semibold text-slate-900 flex items-center space-x-1">
                <span>{user?.full_name || "Gogulnath"}</span>
                <UserCheck className="h-3.5 w-3.5 text-blue-600" />
              </div>
              <div className="text-slate-500 text-[11px]">{user?.role || "Lead QA Engineer"}</div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
