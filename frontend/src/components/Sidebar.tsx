"use client";

import React from "react";
import {
  LayoutDashboard,
  UploadCloud,
  FileSearch,
  ShieldCheck,
  FileCheck2,
  FolderKanban,
  HelpCircle,
} from "lucide-react";

export type NavTab = "dashboard" | "upload" | "inspector" | "standards" | "audit";

interface SidebarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  openDiscrepanciesCount?: number;
}

export default function Sidebar({ activeTab, setActiveTab, openDiscrepanciesCount = 6 }: SidebarProps) {
  const navItems = [
    {
      id: "dashboard" as NavTab,
      label: "Dashboard",
      icon: LayoutDashboard,
      badge: null,
    },
    {
      id: "upload" as NavTab,
      label: "Ingest Manual",
      icon: UploadCloud,
      badge: "AI OCR",
    },
    {
      id: "inspector" as NavTab,
      label: "QC Inspector",
      icon: FileSearch,
      badge: openDiscrepanciesCount > 0 ? `${openDiscrepanciesCount} issues` : null,
      badgeColor: "bg-red-500/20 text-red-300 border-red-500/30",
    },
    {
      id: "standards" as NavTab,
      label: "Standards & Rules",
      icon: ShieldCheck,
      badge: "v1.0",
    },
    {
      id: "audit" as NavTab,
      label: "Compliance Audit",
      icon: FileCheck2,
      badge: null,
    },
  ];

  return (
    <aside className="w-64 border-r border-white/10 bg-[#080c14]/95 flex flex-col justify-between p-4 shrink-0">
      <div className="space-y-6">
        <div>
          <div className="px-3 text-[11px] font-bold tracking-wider text-slate-500 uppercase">
            Platform Navigation
          </div>
          <nav className="mt-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  id={`nav-tab-${item.id}`}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all duration-200 ${
                    isActive
                      ? "bg-gradient-to-r from-cyan-500/20 to-blue-500/10 text-cyan-300 border border-cyan-500/30 shadow-sm shadow-cyan-500/10"
                      : "text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent"
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <Icon className={`h-4 w-4 ${isActive ? "text-cyan-400" : "text-slate-400"}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-mono border ${
                        item.badgeColor
                          ? item.badgeColor
                          : isActive
                          ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/30"
                          : "bg-white/5 text-slate-400 border-white/10"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Project Context */}
        <div className="rounded-xl border border-white/10 bg-slate-900/50 p-3.5">
          <div className="flex items-center space-x-2 text-[11px] font-semibold text-slate-400">
            <FolderKanban className="h-3.5 w-3.5 text-cyan-400" />
            <span>Active Project</span>
          </div>
          <div className="mt-2 text-xs font-bold text-slate-200 truncate">
            Commercial Avionics WD-777
          </div>
          <div className="mt-1 flex items-center justify-between text-[11px] text-slate-400">
            <span>Documents: 14</span>
            <span className="text-emerald-400 font-medium">92% Compliance</span>
          </div>
        </div>
      </div>

      {/* Bottom Help / Engine Version Footnote */}
      <div className="pt-4 border-t border-white/10 space-y-2">
        <div className="flex items-center justify-between text-[11px] text-slate-500">
          <span className="flex items-center space-x-1">
            <HelpCircle className="h-3 w-3" />
            <span>Spandsons Horizon</span>
          </span>
          <span className="font-mono text-[10px]">Build v1.0.4-rc</span>
        </div>
        <div className="text-[10px] text-slate-600 text-center">
          ISO 9001 / AS9100 Verified Architecture
        </div>
      </div>
    </aside>
  );
}
