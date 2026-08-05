"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiFetch } from "@/lib/api";
import { getStoredUserId, setStoredUserId } from "@/lib/user";

interface UserProfile {
  id: string;
  email: string;
  display_name: string | null;
}

interface UserContextValue {
  userId: string | null;
  isLoading: boolean;
  error: string | null;
  bootstrap: (email: string, displayName: string) => Promise<void>;
}

const UserContext = createContext<UserContextValue | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setUserId(getStoredUserId());
    setIsLoading(false);
  }, []);

  const bootstrap = async (email: string, displayName: string) => {
    setError(null);
    try {
      const profile = await apiFetch<UserProfile>("/users/bootstrap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, display_name: displayName }),
      });
      setStoredUserId(profile.id);
      setUserId(profile.id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not set up your account.";
      setError(message);
      throw new Error(message);
    }
  };

  return <UserContext.Provider value={{ userId, isLoading, error, bootstrap }}>{children}</UserContext.Provider>;
}

export function useUser(): UserContextValue {
  const ctx = useContext(UserContext);
  if (!ctx) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return ctx;
  }
