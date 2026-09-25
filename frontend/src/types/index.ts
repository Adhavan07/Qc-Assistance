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
export interface ProcessingJob {
  id: string;
  organization_id: string;
  document_id: string;
  job_type: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | "RETRYING";
  current_step: string;
  progress_percent: number;
  attempts: number;
  max_attempts: number;
  error_message?: string | null;
  result_metadata?: Record<string, any> | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface TitleBlock {
  drawing_number?: string | null;
  title?: string | null;
  revision?: string | null;
  drawn_by?: string | null;
  approved_by?: string | null;
  date?: string | null;
  company_name?: string | null;
}

export interface WireCallout {
  id: string;
  wire_number?: string | null;
  gauge?: string | null;
  color?: string | null;
  from_connector?: string | null;
  to_connector?: string | null;
  raw_text: string;
  location?: BoundingBox | null;
}

export interface Connector {
  id: string;
  ref_des: string;
  part_number?: string | null;
  pin_count?: number | null;
  location?: BoundingBox | null;
}

export interface GeneralNote {
  note_number: number;
  text: string;
  location?: BoundingBox | null;
}

export interface DocumentPage {
  page_number: number;
  width: number;
  height: number;
  title_block?: TitleBlock | null;
  wire_callouts: WireCallout[];
  connectors: Connector[];
  general_notes: GeneralNote[];
  raw_text_blocks: string[];
}

export interface IntermediateDocumentModel {
  document_id: string;
  filename: string;
  page_count: number;
  pages: DocumentPage[];
  metadata: Record<string, any>;
}

export interface PageImageInfo {
  document_id: string;
  page_number: number;
  image_url: string;
  thumbnail_url: string;
  width: number;
  height: number;
}
