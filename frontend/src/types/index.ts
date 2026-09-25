/**
 * TypeScript Data Models for Wiring Diagram QC Assistant
 * Matches backend Pydantic schemas.
 */

export type Severity = "CRITICAL" | "MAJOR" | "MINOR" | "INFO";
export type OverallStatus = "PASS" | "FAIL" | "REVIEW_REQUIRED" | "QUEUED" | "PROCESSING";
export type UserRole = "OWNER" | "ADMIN" | "ENGINEER" | "INSPECTOR" | "VIEWER";

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Confidence {
  level: "HIGH" | "MEDIUM" | "LOW";
  score: number;
}

export interface QCFinding {
  id: string;
  finding_code: string;
  rule_id: string;
  category: string;
  description: string;
  severity: Severity;
  confidence_level: string;
  confidence_score: number;
  page_number: number;
  location_bbox?: BoundingBox | null;
  evidence_text: string;
  requirement_text: string;
  standard_citation: string;
  recommendation: string;
  feedback_status?: "CORRECT" | "INCORRECT" | "NEEDS_REVIEW";
}

export interface QCRunSummary {
  checks_total: number;
  passed: number;
  failed: number;
  review: number;
  critical_count: number;
  major_count: number;
  minor_count: number;
  info_count: number;
}

export interface QCRun {
  id: string;
  organization_id: string;
  document_id: string;
  document_name: string;
  overall_status: OverallStatus;
  checks_total: number;
  checks_passed: number;
  checks_failed: number;
  checks_review: number;
  model_version: string;
  prompt_version: string;
  rules_version: string;
  processing_time_ms: number;
  created_at: string;
  findings: QCFinding[];
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan_tier: string;
  credits_remaining: number;
  created_at?: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  organization_id: string;
  is_active?: boolean;
  created_at?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in_seconds: number;
  user?: User;
  organization?: Organization;
}

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  description?: string | null;
  created_at: string;
  document_count?: number;
}

export interface DocumentItem {
  id: string;
  organization_id: string;
  project_id: string;
  filename: string;
  file_size_bytes: number;
  mime_type: string;
  sha256_checksum: string;
  page_count: number;
  status: string;
  created_at: string;
  is_duplicate?: boolean;
}


