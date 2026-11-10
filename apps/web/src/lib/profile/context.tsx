"use client";

/**
 * Active-profile context for authenticated application routes.
 *
 * Resolves which CareerTwin profile the current user is viewing:
 *   1. an explicit `?profileId=` query parameter (only if the user owns it),
 *   2. the profile saved in localStorage for this user,
 *   3. the user's confirmed profile, otherwise their most recent profile.
 *
 * Profile IDs are stored per authenticated user, so switching accounts never
 * leaks another user's local selection. Ownership is always enforced again by
 * the backend; this context only chooses which owned profile to display.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  listProfiles,
  apiErrorMessage,
  type Profile,
} from "@/lib/api/client";
import { useAuth } from "@/lib/auth/context";

interface ActiveProfileValue {
  profile: Profile | null;
  profileId: string | null;
  profiles: Profile[];
  loading: boolean;
  error: string | null;
  selectProfile: (id: string) => void;
  reload: () => Promise<void>;
}

const ActiveProfileContext = createContext<ActiveProfileValue | null>(null);

const STORAGE_ID = "ct:profileId";
const STORAGE_OWNER = "ct:profileOwner";

function readQueryProfileId(): string | null {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get("profileId");
}

export function ActiveProfileProvider({ children }: { children: ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [profileId, setProfileId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) {
      setProfiles([]);
      setProfileId(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const owned = await listProfiles();
      setProfiles(owned);

      const owner = localStorage.getItem(STORAGE_OWNER);
      let saved = localStorage.getItem(STORAGE_ID);
      if (owner !== user.id) {
        localStorage.removeItem(STORAGE_ID);
        saved = null;
      }
      localStorage.setItem(STORAGE_OWNER, user.id);

      const queryId = readQueryProfileId();
      const candidates = [queryId, saved];
      let selected: Profile | undefined;
      for (const candidate of candidates) {
        if (!candidate) continue;
        selected = owned.find((p) => p.id === candidate);
        if (selected) break;
      }
      if (!selected) {
        selected =
          owned.find((p) => p.profile_status === "CONFIRMED") ?? owned[0];
      }

      if (selected) {
        setProfileId(selected.id);
        localStorage.setItem(STORAGE_ID, selected.id);
      } else {
        setProfileId(null);
      }
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (authLoading) return;
    // Initial/refresh load when the signed-in user changes. `load` resolves
    // the signed-out case too, so the context never stays in a loading state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [authLoading, load]);

  useEffect(() => {
    const handler = () => void load();
    window.addEventListener("ct:profiles-updated", handler);
    return () => window.removeEventListener("ct:profiles-updated", handler);
  }, [load]);

  const selectProfile = useCallback(
    (id: string) => {
      if (!profiles.some((p) => p.id === id)) return;
      setProfileId(id);
      localStorage.setItem(STORAGE_ID, id);
      if (user) localStorage.setItem(STORAGE_OWNER, user.id);
    },
    [profiles, user],
  );

  const profile = useMemo(
    () => profiles.find((p) => p.id === profileId) ?? null,
    [profiles, profileId],
  );

  return (
    <ActiveProfileContext.Provider
      value={{
        profile,
        profileId,
        profiles,
        loading,
        error,
        selectProfile,
        reload: load,
      }}
    >
      {children}
    </ActiveProfileContext.Provider>
  );
}

export function useActiveProfile(): ActiveProfileValue {
  const ctx = useContext(ActiveProfileContext);
  if (!ctx) {
    throw new Error("useActiveProfile must be used within ActiveProfileProvider");
  }
  return ctx;
}

export function notifyProfilesUpdated(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("ct:profiles-updated"));
  }
}
