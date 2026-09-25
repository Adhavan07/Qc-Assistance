"use client";

import React, { useState } from "react";
import Navbar from "../components/Navbar";
import Sidebar, { NavTab } from "../components/Sidebar";
import DashboardView from "../components/DashboardView";
import UploadView from "../components/UploadView";
import SplitScreenViewer from "../components/SplitScreenViewer";
import StandardsView from "../components/StandardsView";
import AuditLogView from "../components/AuditLogView";

export default function Home() {
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");
  const [activeRunId, setActiveRunId] = useState<string>("run-spandsons-demo-01");

  const handleOpenInspector = (runId: string) => {
    setActiveRunId(runId);
    setActiveTab("inspector");
  };

  const handleInspectionReady = (runId: string) => {
    setActiveRunId(runId);
    setActiveTab("inspector");
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#080c14] text-slate-100">
      {/* Top Navbar */}
      <Navbar onUploadClick={() => setActiveTab("upload")} />

      {/* Main Container: Sidebar + Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar Navigation */}
        <Sidebar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          openDiscrepanciesCount={6}
        />

        {/* Dynamic Main Workspace View */}
        <main className="flex-1 overflow-y-auto">
          {activeTab === "dashboard" && (
            <DashboardView
              onOpenInspector={handleOpenInspector}
              onOpenUpload={() => setActiveTab("upload")}
            />
          )}

          {activeTab === "upload" && (
            <UploadView onInspectionReady={handleInspectionReady} />
          )}

          {activeTab === "inspector" && (
            <SplitScreenViewer
              runId={activeRunId}
              onBackToDashboard={() => setActiveTab("dashboard")}
            />
          )}

          {activeTab === "standards" && <StandardsView />}

          {activeTab === "audit" && <AuditLogView />}
        </main>
      </div>
    </div>
  );
}
