"use client";

import React, { useEffect, useState } from "react";
import { X, Users, UserPlus, Building, ShieldAlert, CheckCircle2, Trash2, Edit3, Loader2 } from "lucide-react";
import { useAuth } from "../lib/auth-context";
import { qcApi } from "../lib/api";
import { User, UserRole } from "../types";

interface TeamModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function TeamModal({ isOpen, onClose }: TeamModalProps) {
  const { user, organization, token, updateOrganizationName } = useAuth();
  const [members, setMembers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Invite member form
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState<UserRole>("ENGINEER");
  const [invitePassword, setInvitePassword] = useState("");
  const [showInviteForm, setShowInviteForm] = useState(false);

  // Organization name edit
  const [orgName, setOrgName] = useState(organization?.name || "");
  const [isEditingOrg, setIsEditingOrg] = useState(false);

  const fetchMembers = async () => {
    setIsLoading(true);
    try {
      const data = await qcApi.listMembers(token);
      setMembers(data);
    } catch (err: unknown) {
      setError((err as Error).message || "Failed to load team members");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      setError(null);
      setSuccessMsg(null);
      setOrgName(organization?.name || "");
      fetchMembers();
    }
  }, [isOpen, token, organization]);

  if (!isOpen) return null;

  const handleInviteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setIsLoading(true);
    try {
      await qcApi.inviteMember(
        {
          email: inviteEmail,
          full_name: inviteName,
          role: inviteRole,
          password: invitePassword || "InitialPass123!",
        },
        token
      );
      setSuccessMsg(`Successfully invited ${inviteEmail} as ${inviteRole}`);
      setInviteEmail("");
      setInviteName("");
      setInvitePassword("");
      setShowInviteForm(false);
      await fetchMembers();
    } catch (err: unknown) {
      setError((err as Error).message || "Failed to invite member");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRoleChange = async (memberId: string, newRole: string) => {
    setError(null);
    setSuccessMsg(null);
    try {
      await qcApi.updateMember(memberId, { role: newRole }, token);
      setSuccessMsg("Member role updated");
      await fetchMembers();
    } catch (err: unknown) {
      setError((err as Error).message || "Failed to update member role");
    }
  };

  const handleDeleteMember = async (memberId: string, email: string) => {
    if (!confirm(`Are you sure you want to remove member ${email}?`)) return;
    setError(null);
    setSuccessMsg(null);
    try {
      await qcApi.deleteMember(memberId, token);
      setSuccessMsg(`Member ${email} removed`);
      await fetchMembers();
    } catch (err: unknown) {
      setError((err as Error).message || "Failed to remove member");
    }
  };

  const handleOrgNameSave = async () => {
    if (!orgName.trim()) return;
    const ok = await updateOrganizationName(orgName.trim());
    if (ok) {
      setIsEditingOrg(false);
      setSuccessMsg("Organization details saved");
    }
  };

  const canManageTeam = user?.role === "OWNER" || user?.role === "ADMIN";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
      <div className="relative w-full max-w-2xl rounded-2xl bg-white p-6 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
              <Building className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Tenant Organization & Team
              </h3>
              <p className="text-xs text-slate-500">
                Multi-Tenant Scoping & Role-Based Access Control
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Feedback banners */}
        {error && (
          <div className="mt-4 flex items-center space-x-2 rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700">
            <ShieldAlert className="h-4 w-4 shrink-0 text-rose-600" />
            <span>{error}</span>
          </div>
        )}
        {successMsg && (
          <div className="mt-4 flex items-center space-x-2 rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-xs text-emerald-800">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Tenant Profile Card */}
        <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-500">
                Organization Tenant Profile
              </span>
              {isEditingOrg ? (
                <div className="mt-1 flex items-center space-x-2">
                  <input
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    className="rounded border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-900 focus:outline-none focus:border-blue-600"
                  />
                  <button
                    onClick={handleOrgNameSave}
                    className="rounded bg-blue-600 px-2 py-1 text-xs font-medium text-white hover:bg-blue-700 cursor-pointer"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setIsEditingOrg(false)}
                    className="rounded bg-slate-200 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-300 cursor-pointer"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <div className="flex items-center space-x-2">
                  <h4 className="text-sm font-bold text-slate-900">
                    {organization?.name || "Spandsons Horizon Engineering Pvt. Ltd."}
                  </h4>
                  {canManageTeam && (
                    <button
                      onClick={() => setIsEditingOrg(true)}
                      className="text-slate-400 hover:text-slate-600 cursor-pointer"
                      title="Edit organization name"
                    >
                      <Edit3 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              )}
            </div>
            <div className="text-right">
              <span className="inline-block rounded-md bg-blue-50 border border-blue-200 px-2 py-0.5 text-[10px] font-mono font-semibold text-blue-700 uppercase">
                {organization?.slug || "spandsons-horizon"}
              </span>
              <p className="mt-0.5 text-xs text-slate-500">
                QC Credits: <span className="font-bold text-slate-800">{organization?.credits_remaining ?? 3}</span>
              </p>
            </div>
          </div>
        </div>

        {/* Team Members List */}
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <Users className="h-4 w-4 text-slate-600" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Team Members ({members.length})
              </h4>
            </div>
            {canManageTeam && (
              <button
                onClick={() => setShowInviteForm(!showInviteForm)}
                className="flex items-center space-x-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition-colors cursor-pointer"
              >
                <UserPlus className="h-3.5 w-3.5" />
                <span>{showInviteForm ? "Close Form" : "Invite Member"}</span>
              </button>
            )}
          </div>

          {/* Invite form collapsible */}
          {showInviteForm && (
            <form
              onSubmit={handleInviteSubmit}
              className="mb-4 rounded-xl border border-blue-200 bg-blue-50/50 p-4 space-y-3 animate-in fade-in duration-150"
            >
              <h5 className="text-xs font-bold text-blue-900">Provision New Organization Member</h5>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                    Full Name
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Ananya Roy"
                    value={inviteName}
                    onChange={(e) => setInviteName(e.target.value)}
                    className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs text-slate-900 focus:border-blue-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                    Email Address
                  </label>
                  <input
                    type="email"
                    required
                    placeholder="name@company.com"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs text-slate-900 focus:border-blue-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                    Assigned RBAC Role
                  </label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value as UserRole)}
                    className="w-full rounded border border-slate-300 px-2 py-1.5 text-xs text-slate-900 focus:border-blue-600 focus:outline-none bg-white"
                  >
                    <option value="ADMIN">ADMIN (Member & Project Management)</option>
                    <option value="ENGINEER">ENGINEER (Upload Diagrams & Run QC)</option>
                    <option value="INSPECTOR">INSPECTOR (Review Findings & Verify)</option>
                    <option value="VIEWER">VIEWER (Read-Only QC Reports)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                    Initial Password (min 8 chars)
                  </label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    placeholder="••••••••"
                    value={invitePassword}
                    onChange={(e) => setInvitePassword(e.target.value)}
                    className="w-full rounded border border-slate-300 px-2.5 py-1.5 text-xs text-slate-900 focus:border-blue-600 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex justify-end pt-1">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex items-center space-x-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700 cursor-pointer disabled:opacity-50"
                >
                  {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  <span>Send Member Invitation</span>
                </button>
              </div>
            </form>
          )}

          {/* Members Table */}
          <div className="overflow-hidden rounded-xl border border-slate-200">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-2.5 px-3">Member</th>
                  <th className="py-2.5 px-3">Email</th>
                  <th className="py-2.5 px-3">Role</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {members.map((m) => {
                  const isCurrent = m.id === user?.id;
                  const isOwner = m.role === "OWNER";
                  return (
                    <tr key={m.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-2.5 px-3 font-medium text-slate-900 flex items-center space-x-2">
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-slate-700 font-bold text-xs border border-slate-200">
                          {m.full_name ? m.full_name[0] : "U"}
                        </div>
                        <div>
                          <span>{m.full_name}</span>
                          {isCurrent && (
                            <span className="ml-1.5 rounded bg-blue-100 px-1.5 py-0.2 text-[9px] font-bold text-blue-700">
                              YOU
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-slate-600 font-mono text-[11px]">{m.email}</td>
                      <td className="py-2.5 px-3">
                        {canManageTeam && !isOwner && !isCurrent ? (
                          <select
                            value={m.role}
                            onChange={(e) => handleRoleChange(m.id, e.target.value)}
                            className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-800 font-semibold focus:border-blue-600 focus:outline-none"
                          >
                            <option value="ADMIN">ADMIN</option>
                            <option value="ENGINEER">ENGINEER</option>
                            <option value="INSPECTOR">INSPECTOR</option>
                            <option value="VIEWER">VIEWER</option>
                          </select>
                        ) : (
                          <span
                            className={`inline-block rounded-md px-2 py-0.5 text-[10px] font-bold ${
                              m.role === "OWNER"
                                ? "bg-amber-100 text-amber-800 border border-amber-200"
                                : m.role === "ADMIN"
                                ? "bg-blue-100 text-blue-800 border border-blue-200"
                                : "bg-slate-100 text-slate-700 border border-slate-200"
                            }`}
                          >
                            {m.role}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {canManageTeam && !isCurrent && !isOwner && (
                          <button
                            onClick={() => handleDeleteMember(m.id, m.email)}
                            className="text-slate-400 hover:text-rose-600 p-1 transition-colors cursor-pointer"
                            title="Remove member"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
