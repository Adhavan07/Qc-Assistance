"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { Organization, User } from "../types";
import { qcApi } from "./api";
import { MOCK_ORGANIZATION, MOCK_USER } from "./mockData";

interface AuthContextType {
  user: User | null;
  organization: Organization | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  clearError: () => void;
  login: (email: string, password: string) => Promise<boolean>;
  register: (
    orgName: string,
    orgSlug: string,
    fullName: string,
    email: string,
    password: string
  ) => Promise<boolean>;
  logout: () => Promise<void>;
  updateProfile: (fullName: string) => Promise<boolean>;
  updateOrganizationName: (name: string) => Promise<boolean>;
  deductCredit: () => void;
  addCredits: (amount: number) => void;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(MOCK_USER);
  const [organization, setOrganization] = useState<Organization | null>(MOCK_ORGANIZATION);
  const [token, setToken] = useState<string | null>("mock-jwt-token-spandsons");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = () => setError(null);

  // Initialize session from localStorage or active token
  useEffect(() => {
    try {
      const savedToken = localStorage.getItem("qc_auth_token");
      if (savedToken) {
        setToken(savedToken);
        // Refresh profile from server
        qcApi.getCurrentUser(savedToken)
          .then((u) => {
            if (u && u.id) setUser(u);
          })
          .catch(() => {
            // Keep current user state
          });

        qcApi.getCurrentOrganization(savedToken)
          .then((o) => {
            if (o && o.id) setOrganization(o);
          })
          .catch(() => {
            // Keep current org state
          });
      }
    } catch {
      // Ignore SSR / localStorage errors
    }
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await qcApi.login({ email, password });
      setToken(res.access_token);
      try {
        localStorage.setItem("qc_auth_token", res.access_token);
        if (res.refresh_token) {
          localStorage.setItem("qc_refresh_token", res.refresh_token);
        }
      } catch {
        // Ignore storage errors
      }

      if (res.user) {
        setUser(res.user);
      } else {
        const u = await qcApi.getCurrentUser(res.access_token);
        setUser(u);
      }

      if (res.organization) {
        setOrganization(res.organization);
      } else {
        const o = await qcApi.getCurrentOrganization(res.access_token);
        setOrganization(o);
      }
      setIsLoading(false);
      return true;
    } catch (err: unknown) {
      setError((err as Error).message || "Login failed");
      setIsLoading(false);
      return false;
    }
  };

  const register = async (
    orgName: string,
    orgSlug: string,
    fullName: string,
    email: string,
    password: string
  ): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await qcApi.register({
        organization_name: orgName,
        organization_slug: orgSlug,
        full_name: fullName,
        email,
        password,
      });

      setToken(res.access_token);
      try {
        localStorage.setItem("qc_auth_token", res.access_token);
        if (res.refresh_token) {
          localStorage.setItem("qc_refresh_token", res.refresh_token);
        }
      } catch {
        // Ignore
      }

      if (res.user) setUser(res.user);
      if (res.organization) setOrganization(res.organization);

      setIsLoading(false);
      return true;
    } catch (err: unknown) {
      setError((err as Error).message || "Registration failed");
      setIsLoading(false);
      return false;
    }
  };

  const logout = async (): Promise<void> => {
    try {
      if (token && !token.startsWith("mock-")) {
        await qcApi.logout(token);
      }
    } catch {
      // Ignore network errors on logout
    } finally {
      setUser(null);
      setOrganization(null);
      setToken(null);
      try {
        localStorage.removeItem("qc_auth_token");
        localStorage.removeItem("qc_refresh_token");
      } catch {
        // Ignore
      }
    }
  };

  const updateProfile = async (fullName: string): Promise<boolean> => {
    try {
      const updated = await qcApi.updateCurrentUserProfile({ full_name: fullName }, token);
      setUser(updated);
      return true;
    } catch (err: unknown) {
      setError((err as Error).message || "Failed to update profile");
      return false;
    }
  };

  const updateOrganizationName = async (name: string): Promise<boolean> => {
    try {
      const updated = await qcApi.updateCurrentOrganization({ name }, token);
      setOrganization(updated);
      return true;
    } catch (err: unknown) {
      setError((err as Error).message || "Failed to update organization");
      return false;
    }
  };

  const refreshSession = async () => {
    if (!token) return;
    try {
      const u = await qcApi.getCurrentUser(token);
      if (u) setUser(u);
      const o = await qcApi.getCurrentOrganization(token);
      if (o) setOrganization(o);
    } catch {
      // Ignore
    }
  };

  const deductCredit = () => {
    if (organization && organization.credits_remaining > 0) {
      setOrganization({
        ...organization,
        credits_remaining: organization.credits_remaining - 1,
      });
    }
  };

  const addCredits = (amount: number) => {
    if (organization) {
      setOrganization({
        ...organization,
        credits_remaining: organization.credits_remaining + amount,
      });
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        organization,
        token,
        isLoading,
        error,
        clearError,
        login,
        register,
        logout,
        updateProfile,
        updateOrganizationName,
        deductCredit,
        addCredits,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

