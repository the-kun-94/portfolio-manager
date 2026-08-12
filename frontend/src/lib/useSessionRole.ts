import { useEffect, useState } from "react";

export type SessionRole = "write" | "read" | null;

// Fetches this browser's session role once on mount, purely for UI gating
// (disabling trade/park controls for a read-only visitor) — the real
// enforcement is server-side, see pages/api/proxy/[...path].ts.
export function useSessionRole(): SessionRole {
  const [role, setRole] = useState<SessionRole>(null);

  useEffect(() => {
    fetch("/api/session")
      .then((res) => res.json())
      .then((data) => setRole(data?.role ?? null))
      .catch(() => setRole(null));
  }, []);

  return role;
}
