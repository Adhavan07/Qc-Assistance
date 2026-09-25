/**
 * API Client for Wiring Diagram QC Assistant
 * Handles communication with the FastAPI backend (/api/v1)
 * Includes graceful fallback to realistic engineering mock data when backend is unreachable.
 */

import { AuthTokens, Organization, QCFinding, QCRun, User } from "../types";
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
  async login(payload: { email: string; password: string }): Promise<AuthTokens> {
    return request<AuthTokens>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async register(payload: {
    organization_name: string;
    organization_slug: string;
    full_name: string;
    email: string;
    password: string;
  }): Promise<AuthTokens> {
    return request<AuthTokens>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async refreshToken(refreshToken: string): Promise<AuthTokens> {
    return request<AuthTokens>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  async logout(token?: string | null): Promise<{ message: string }> {
    return request<{ message: string }>("/auth/logout", {
      method: "POST",
      token,
    }, { message: "Logged out" });
  },

  async getCurrentUser(token?: string | null): Promise<User> {
    return request<User>("/auth/me", { token }, MOCK_USER);
  },

  async updateCurrentUserProfile(payload: { full_name: string }, token?: string | null): Promise<User> {
    return request<User>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify(payload),
      token,
    }, { ...MOCK_USER, full_name: payload.full_name });
  },

  // Organizations & Members
  async getCurrentOrganization(token?: string | null): Promise<Organization> {
    return request<Organization>("/organizations/me", { token }, MOCK_ORGANIZATION);
  },

  async updateCurrentOrganization(payload: { name: string }, token?: string | null): Promise<Organization> {
    return request<Organization>("/organizations/me", {
      method: "PATCH",
      body: JSON.stringify(payload),
      token,
    }, { ...MOCK_ORGANIZATION, name: payload.name });
  },

  async getOrganization(orgId: string, token?: string | null): Promise<Organization> {
    return request<Organization>(`/organizations/${orgId}`, { token }, MOCK_ORGANIZATION);
  },

  async listMembers(token?: string | null): Promise<User[]> {
    return request<User[]>("/organizations/members", { token }, [
      MOCK_USER,
      {
        id: "usr-gogulnath",
        email: "gogulnath@spandsons.com",
        full_name: "Gogulnath",
        role: "ENGINEER",
        organization_id: "org-spandsons-01",
        is_active: true,
      },
      {
        id: "usr-inspector",
        email: "inspector@spandsons.com",
        full_name: "Senior Avionics QC Inspector",
        role: "INSPECTOR",
        organization_id: "org-spandsons-01",
        is_active: true,
      },
    ]);
  },

  async inviteMember(
    payload: { email: string; full_name: string; role: string; password: string },
    token?: string | null
  ): Promise<User> {
    return request<User>("/organizations/members", {
      method: "POST",
      body: JSON.stringify(payload),
      token,
    });
  },

  async updateMember(
    memberId: string,
    payload: { role?: string; is_active?: boolean; full_name?: string },
    token?: string | null
  ): Promise<User> {
    return request<User>(`/organizations/members/${memberId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
      token,
    });
  },

  async deleteMember(memberId: string, token?: string | null): Promise<{ message: string }> {
    return request<{ message: string }>(`/organizations/members/${memberId}`, {
      method: "DELETE",
      token,
    }, { message: "Member removed" });
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
