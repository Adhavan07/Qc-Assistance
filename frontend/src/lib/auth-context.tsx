"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { Organization, User } from "../types";
import { MOCK_ORGANIZATION, MOCK_USER } from "./mockData";

interface AuthContextType {
  user: User | null;
  organization: Organization | null;
  token: string | null;
  isLoading: boolean;
  deductCredit: () => void;
  addCredits: (amount: number) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(MOCK_USER);
  const [organization, setOrganization] = useState<Organization | null>(MOCK_ORGANIZATION);
  const [token, setToken] = useState<string | null>("mock-jwt-token-spandsons");
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    // Check localStorage for saved session token if available
    try {
      const savedToken = localStorage.getItem("qc_auth_token");
      if (savedToken) {
        setToken(savedToken);
      }
    } catch {
      // Ignore SSR / localStorage errors
    }
  }, []);

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

  const logout = () => {
    setUser(null);
    setOrganization(null);
    setToken(null);
    try {
      localStorage.removeItem("qc_auth_token");
    } catch {
      // Ignore
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        organization,
        token,
        isLoading,
        deductCredit,
        addCredits,
        logout,
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
