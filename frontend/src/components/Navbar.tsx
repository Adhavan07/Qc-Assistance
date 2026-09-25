"use client";

import React, { useState } from "react";
import {
  Cpu,
  Zap,
  Shield,
  Sparkles,
  UserCheck,
  Users,
  LogIn,
  LogOut,
  ChevronDown,
} from "lucide-react";
import { useAuth } from "../lib/auth-context";
import AuthModal from "./AuthModal";
import TeamModal from "./TeamModal";

interface NavbarProps {
  onUploadClick: () => void;
}

export default function Navbar({ onUploadClick }: NavbarProps) {
  const { user, organization, logout } = useAuth();
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isTeamOpen, setIsTeamOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  return (
    <>
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
                <button
                  onClick={() => setIsTeamOpen(true)}
                  className="flex items-center space-x-1 text-xs text-slate-500 font-medium hover:text-blue-600 transition-colors cursor-pointer text-left"
                  title="Click to view Organization & Team"
                >
                  <span>{organization?.name || "Spandsons Horizon Engineering Pvt. Ltd."}</span>
                  <Users className="h-3 w-3 text-slate-400" />
                </button>
              </div>
            </div>

            <div className="hidden lg:flex items-center space-x-2 pl-4 border-l border-slate-200">
              <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs text-slate-700">
                <Shield className="h-3.5 w-3.5 text-blue-600" />
                <span className="font-mono text-[11px] font-medium text-slate-800">
                  IPC-WHMA-A-620D Cl.3
                </span>
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
            <button
              onClick={() => setIsTeamOpen(true)}
              className="flex items-center space-x-2 bg-amber-50/80 border border-amber-200 rounded-lg px-3 py-1.5 hover:bg-amber-100/70 transition-colors cursor-pointer text-left"
              title="Click to manage tenant credits and tier"
            >
              <Zap className="h-4 w-4 text-amber-600 fill-amber-500" />
              <div className="text-right">
                <div className="text-xs font-bold text-amber-950">
                  {organization?.credits_remaining ?? 3}{" "}
                  <span className="font-normal text-amber-800/80">credits</span>
                </div>
                <div className="text-[10px] text-amber-700 font-mono uppercase tracking-wider font-semibold">
                  {organization?.plan_tier || "Enterprise"} Plan
                </div>
              </div>
            </button>

            {/* Quick Upload CTA */}
            <button
              onClick={onUploadClick}
              id="nav-quick-upload-btn"
              className="flex items-center space-x-2 rounded-lg bg-blue-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition-all hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
            >
              <Sparkles className="h-4 w-4" />
              <span>New Inspection</span>
            </button>

            {/* User Profile & Menu */}
            <div className="relative pl-2 border-l border-slate-200">
              <button
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                className="flex items-center space-x-2 p-1 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer text-left"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 border border-blue-200 text-sm font-bold text-blue-700">
                  {user?.full_name ? user.full_name[0] : "P"}
                </div>
                <div className="hidden xl:block text-left text-xs">
                  <div className="font-semibold text-slate-900 flex items-center space-x-1">
                    <span>{user?.full_name || "Pravin Kumar"}</span>
                    <UserCheck className="h-3.5 w-3.5 text-blue-600" />
                  </div>
                  <div className="text-slate-500 text-[11px]">{user?.role || "OWNER"}</div>
                </div>
                <ChevronDown className="h-3.5 w-3.5 text-slate-400 hidden xl:block" />
              </button>

              {/* User Dropdown */}
              {isUserMenuOpen && (
                <div className="absolute right-0 mt-2 w-52 rounded-xl bg-white p-2 shadow-xl border border-slate-200 z-50 text-xs">
                  <div className="px-3 py-2 border-b border-slate-100 mb-1">
                    <p className="font-semibold text-slate-900">{user?.full_name || "User"}</p>
                    <p className="text-[11px] text-slate-500 font-mono truncate">{user?.email}</p>
                    <span className="mt-1 inline-block rounded bg-blue-50 px-1.5 py-0.2 text-[9px] font-bold text-blue-700 border border-blue-200">
                      {user?.role || "VIEWER"}
                    </span>
                  </div>

                  <button
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      setIsTeamOpen(true);
                    }}
                    className="w-full flex items-center space-x-2 px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer text-left"
                  >
                    <Users className="h-4 w-4 text-slate-500" />
                    <span>Organization & Team</span>
                  </button>

                  <button
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      setIsAuthOpen(true);
                    }}
                    className="w-full flex items-center space-x-2 px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer text-left"
                  >
                    <LogIn className="h-4 w-4 text-slate-500" />
                    <span>Switch Tenant / Sign In</span>
                  </button>

                  <div className="border-t border-slate-100 mt-1 pt-1">
                    <button
                      onClick={async () => {
                        setIsUserMenuOpen(false);
                        await logout();
                      }}
                      className="w-full flex items-center space-x-2 px-3 py-2 rounded-lg text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer text-left font-semibold"
                    >
                      <LogOut className="h-4 w-4 text-rose-500" />
                      <span>Log Out</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Auth and Team Modals */}
      <AuthModal isOpen={isAuthOpen} onClose={() => setIsAuthOpen(false)} />
      <TeamModal isOpen={isTeamOpen} onClose={() => setIsTeamOpen(false)} />
    </>
  );
}

