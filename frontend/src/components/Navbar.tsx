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
    <header className="sticky top-0 z-40 w-full border-b border-white/10 bg-[#080c14]/90 backdrop-blur-xl">
      <div className="flex h-16 items-center justify-between px-6">
        {/* Left: Brand & Engineering Workspace Indicator */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 via-sky-600 to-blue-700 shadow-lg shadow-cyan-500/20">
              <Cpu className="h-5 w-5 text-white" />
              <span className="absolute -bottom-0.5 -right-0.5 flex h-3 w-3">
                <span className="live-pulse absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500 border border-[#080c14]"></span>
              </span>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold tracking-tight text-white text-base">
                  Wiring Diagram QC
                </span>
                <span className="rounded bg-cyan-950/80 px-1.5 py-0.5 text-[10px] font-semibold tracking-wider text-cyan-300 border border-cyan-500/30 uppercase">
                  AI SaaS
                </span>
              </div>
              <p className="text-xs text-slate-400 font-medium">
                {organization?.name || "Spandsons Horizon Engineering"}
              </p>
            </div>
          </div>

          <div className="hidden lg:flex items-center space-x-2 pl-4 border-l border-white/10">
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-slate-300">
              <Shield className="h-3.5 w-3.5 text-cyan-400" />
              <span className="font-mono text-[11px] text-cyan-200">IPC-WHMA-A-620D Cl.3</span>
            </div>
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-slate-300">
              <span className="font-mono text-[11px] text-amber-200">UL 508A</span>
            </div>
          </div>
        </div>

        {/* Center: System Operational Status */}
        <div className="hidden md:flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="font-medium">Hybrid AI QC Engine v1.0 Online</span>
          <span className="text-emerald-500/60 font-mono text-[10px]">• Latency: 1.8s</span>
        </div>

        {/* Right: Credits, New Inspection CTA & User Profile */}
        <div className="flex items-center space-x-3">
          {/* Credit Meter */}
          <div className="flex items-center space-x-2 bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/30 rounded-lg px-3 py-1.5">
            <Zap className="h-4 w-4 text-amber-400 fill-amber-400" />
            <div className="text-right">
              <div className="text-xs font-bold text-amber-200">
                {organization?.credits_remaining ?? 248} <span className="font-normal text-amber-300/80">credits</span>
              </div>
              <div className="text-[10px] text-amber-400/70 font-mono uppercase tracking-wider">
                {organization?.plan_tier || "Enterprise"}
              </div>
            </div>
          </div>

          {/* Quick Upload CTA */}
          <button
            onClick={onUploadClick}
            id="nav-quick-upload-btn"
            className="flex items-center space-x-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-3.5 py-2 text-xs font-semibold text-white shadow-md shadow-cyan-600/30 transition-all duration-200 hover:from-cyan-500 hover:to-blue-500 hover:shadow-cyan-500/50 hover:scale-[1.02] active:scale-[0.98]"
          >
            <Sparkles className="h-4 w-4" />
            <span>New Inspection</span>
          </button>

          {/* User Profile */}
          <div className="flex items-center space-x-2.5 pl-2 border-l border-white/10">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-800 border border-slate-700 text-sm font-bold text-cyan-400">
              {user?.full_name ? user.full_name[0] : "G"}
            </div>
            <div className="hidden xl:block text-left text-xs">
              <div className="font-semibold text-slate-200 flex items-center space-x-1">
                <span>{user?.full_name || "Gogulnath"}</span>
                <UserCheck className="h-3 w-3 text-cyan-400" />
              </div>
              <div className="text-slate-400 text-[11px]">{user?.role || "Lead QA Engineer"}</div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
