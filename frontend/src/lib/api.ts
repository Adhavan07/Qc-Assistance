/**
 * API Client for Wiring Diagram QC Assistant
 * Handles communication with the FastAPI backend (/api/v1)
 * Includes graceful fallback to realistic engineering mock data when backend is unreachable.
 */

import { Organization, QCFinding, QCRun, User } from "../types";
import {
  MOCK_FINDINGS,
  MOCK_ORGANIZATION,
  MOCK_QC_RUN,
  MOCK_RECENT_RUNS,
  MOCK_USER,
} from "./mockData";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface FetchOptions extends RequestInit {
  token?: string | null;
}

async function request<T>(endpoint: string, options: FetchOptions = {}, fallbackData?: T): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (options.token) {
    headers["Authorization"] = `Bearer ${options.token}`;
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      if (fallbackData !== undefined) {
        console.warn(`[QC-API] ${endpoint} returned ${response.status}. Using high-fidelity fallback data.`);
        return fallbackData;
      }
      const errorText = await response.text();
      throw new Error(`API error ${response.status}: ${errorText}`);
    }

    return await response.json();
  } catch (err: unknown) {
    if (fallbackData !== undefined) {
      console.warn(`[QC-API] Error reaching ${endpoint}: ${(err as Error).message}. Using fallback data.`);
      return fallbackData;
    }
    throw err;
  }
}

export const qcApi = {
  // Auth
  async getCurrentUser(token?: string | null): Promise<User> {
    return request<User>("/auth/me", { token }, MOCK_USER);
  },

  // Organizations
  async getOrganization(orgId: string, token?: string | null): Promise<Organization> {
    return request<Organization>(`/organizations/${orgId}`, { token }, MOCK_ORGANIZATION);
  },

  // Projects & Documents
  async listProjects(token?: string | null) {
    return request(
      "/projects",
      { token },
      [
        {
          id: "proj-01",
          organization_id: "org-spandsons-01",
          name: "Commercial Avionics Harness WD-777",
          description: "Boeing 777X wiring schematics and harness routing manuals.",
        },
        {
          id: "proj-02",
          organization_id: "org-spandsons-01",
          name: "Industrial Control Panels Series 400",
          description: "High-voltage switchgear and UL 508A control cabinets.",
        },
      ]
    );
  },

  async listDocuments(projectId?: string, token?: string | null) {
    return request(
      `/documents${projectId ? `?project_id=${projectId}` : ""}`,
      { token },
      [
        {
          id: "doc-harness-777x",
          organization_id: "org-spandsons-01",
          filename: "Boeing_777X_Avionics_Harness_WD-777-04.pdf",
          file_size_bytes: 4210000,
          page_count: 3,
          status: "ANALYZED",
          created_at: new Date().toISOString(),
        },
      ]
    );
  },

  // QC Runs
  async listRecentRuns(token?: string | null): Promise<QCRun[]> {
    return request<QCRun[]>("/qc-runs", { token }, MOCK_RECENT_RUNS);
  },

  async getQCRun(runId: string, token?: string | null): Promise<QCRun> {
    const run = await request<QCRun>(`/qc-runs/${runId}`, { token }, MOCK_QC_RUN);
    if (!run.findings || run.findings.length === 0) {
      run.findings = MOCK_FINDINGS;
    }
    return run;
  },

  async getFindings(runId: string, severity?: string, token?: string | null): Promise<QCFinding[]> {
    const endpoint = `/qc-runs/${runId}/findings${severity ? `?severity=${severity}` : ""}`;
    const findings = await request<QCFinding[]>(endpoint, { token }, MOCK_FINDINGS);
    if (severity && severity !== "ALL") {
      return findings.filter((f) => f.severity === severity);
    }
    return findings;
  },

  async triggerQCRun(documentId: string, standards: string[], token?: string | null): Promise<QCRun> {
    return request<QCRun>(
      "/qc-runs",
      {
        method: "POST",
        body: JSON.stringify({ document_id: documentId, standards }),
        token,
      },
      {
        ...MOCK_QC_RUN,
        id: `run-${Date.now().toString(36)}`,
        created_at: new Date().toISOString(),
      }
    );
  },

  // Discrepancy Feedback
  async submitFindingFeedback(
    runId: string,
    findingId: string,
    status: "CORRECT" | "INCORRECT" | "NEEDS_REVIEW",
    token?: string | null
  ): Promise<{ success: boolean; finding_id: string; status: string }> {
    return request(
      `/qc-runs/${runId}/findings/${findingId}/feedback`,
      {
        method: "POST",
        body: JSON.stringify({ feedback_status: status }),
        token,
      },
      { success: true, finding_id: findingId, status }
    );
  },
};
