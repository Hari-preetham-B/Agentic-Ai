"use client";

/**
 * Authentication context.
 *
 * When Supabase public credentials are configured, this uses real Supabase
 * authentication (session persistence, refresh, JWTs verified by the FastAPI
 * backend through JWKS). Secrets and service-role keys never reach the browser.
 *
 * When Supabase is NOT configured, local development and automated demos fall
 * back to the backend's FakeAuthProvider. That fallback is explicitly labelled
 * in the UI, uses a deterministic local identity, and is disabled in
 * production builds and whenever Supabase is configured.
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { getSupabaseClient, isSupabaseConfigured } from "@/lib/supabase/client";
import { setAuthToken } from "@/lib/api/client";
import type { User, Session } from "@supabase/supabase-js";

export type AuthMode = "supabase" | "development" | "disabled";

interface AuthContextValue {
  user: User | null;
  session: Session | null;
  loading: boolean;
  isConfigured: boolean;
  authMode: AuthMode;
  signUp: (email: string, password: string) => Promise<{ error: string | null }>;
  signIn: (email: string, password: string) => Promise<{ error: string | null }>;
  signOut: () => Promise<void>;
  getAccessToken: () => string | null;
}

const DEV_USER_ID = "0d000000-0000-4000-8000-000000000001";
const DEV_EMAIL = "local@careertwin.dev";
const DEV_TOKEN = `fake:${DEV_USER_ID}:${DEV_EMAIL}`;

const AuthContext = createContext<AuthContextValue | null>(null);

function makeDevUser(): User {
  return {
    id: DEV_USER_ID,
    email: DEV_EMAIL,
    app_metadata: { provider: "fake" },
    user_metadata: { name: "Local development user" },
    aud: "authenticated",
    created_at: new Date(0).toISOString(),
  } as User;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const isConfigured = isSupabaseConfigured();
  const devFallback =
    !isConfigured && process.env.NODE_ENV !== "production";
  // In development without Supabase, the local fake identity is created up
  // front (not inside an effect) so child effects never run before the token
  // is set. The token is a constant and the fallback is disabled in
  // production builds.
  const [user, setUser] = useState<User | null>(() => {
    if (devFallback) {
      setAuthToken(DEV_TOKEN);
      return makeDevUser();
    }
    return null;
  });
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(!devFallback);

  useEffect(() => {
    const supabase = getSupabaseClient();
    if (!supabase) {
      // Nothing to subscribe to. Without a dev fallback (production without
      // Supabase configured) the user simply stays signed out.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLoading(false);
      return;
    }

    let active = true;
    supabase.auth
      .getSession()
      .then(({ data: { session: s } }) => {
        if (!active) return;
        setSession(s);
        setUser(s?.user ?? null);
        setAuthToken(s?.access_token ?? null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, s) => {
        setSession(s);
        setUser(s?.user ?? null);
        setAuthToken(s?.access_token ?? null);
      },
    );

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  const signUp = useCallback(
    async (email: string, password: string) => {
      const supabase = getSupabaseClient();
      if (!supabase) return { error: "Supabase is not configured." };
      const { error } = await supabase.auth.signUp({ email, password });
      return { error: error?.message ?? null };
    },
    [],
  );

  const signIn = useCallback(
    async (email: string, password: string) => {
      const supabase = getSupabaseClient();
      if (!supabase) return { error: "Supabase is not configured." };
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      return { error: error?.message ?? null };
    },
    [],
  );

  const signOut = useCallback(async () => {
    const supabase = getSupabaseClient();
    if (supabase) {
      await supabase.auth.signOut();
    }
    setSession(null);
    setUser(null);
    setAuthToken(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem("ct:profileId");
      localStorage.removeItem("ct:profileOwner");
    }
  }, []);

  const getAccessToken = useCallback(() => {
    return session?.access_token ?? null;
  }, [session]);

  const authMode: AuthMode = isConfigured
    ? "supabase"
    : devFallback
      ? "development"
      : "disabled";

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        loading,
        isConfigured,
        authMode,
        signUp,
        signIn,
        signOut,
        getAccessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
