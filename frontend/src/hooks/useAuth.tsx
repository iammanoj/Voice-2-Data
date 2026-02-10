import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { jwtDecode } from "jwt-decode";

interface User {
  name: string;
  email: string;
  picture: string;
}

interface StoredSession {
  user: User;
  credential: string;
  exp: number;
}

interface AuthContextValue {
  user: User | null;
  /** Raw Google JWT — store for future backend forwarding. */
  credential: string | null;
  /** Returns an error message on failure, or null on success. */
  login: (credential: string) => string | null;
  logout: () => void;
}

interface GoogleJwtPayload {
  iss: string;
  aud: string;
  exp: number;
  name: string;
  email: string;
  picture: string;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const SESSION_KEY = "v2d_auth";
const EXPECTED_ISSUERS = ["https://accounts.google.com", "accounts.google.com"];

/**
 * Validates claims (iss, aud, exp) from the Google JWT.
 *
 * NOTE: This does NOT verify the cryptographic signature — that requires
 * fetching Google's JWKS and is best done server-side. The credential
 * comes directly from Google's Identity Services SDK, so the main risk
 * is sessionStorage tampering (which bypasses any client-side check).
 * For backend-enforced auth, forward `credential` as a Bearer token and
 * verify with google-auth on the server.
 */
function validateGoogleJwt(credential: string): { user: User; exp: number } {
  const decoded = jwtDecode<GoogleJwtPayload>(credential);

  if (!EXPECTED_ISSUERS.includes(decoded.iss)) {
    throw new Error(`Invalid token issuer: ${decoded.iss}`);
  }

  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? "";
  if (decoded.aud !== clientId) {
    throw new Error("Token audience does not match client ID");
  }

  const nowSeconds = Math.floor(Date.now() / 1000);
  if (decoded.exp < nowSeconds) {
    throw new Error("Token has expired");
  }

  return {
    user: { name: decoded.name, email: decoded.email, picture: decoded.picture },
    exp: decoded.exp,
  };
}

function restoreSession(): StoredSession | null {
  const stored = sessionStorage.getItem(SESSION_KEY);
  if (!stored) return null;
  try {
    const session: StoredSession = JSON.parse(stored);
    const nowSeconds = Math.floor(Date.now() / 1000);
    if (session.exp < nowSeconds) {
      sessionStorage.removeItem(SESSION_KEY);
      return null;
    }
    return session;
  } catch {
    sessionStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(restoreSession);

  const login = useCallback((credential: string): string | null => {
    try {
      const { user, exp } = validateGoogleJwt(credential);
      const s: StoredSession = { user, credential, exp };
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(s));
      setSession(s);
      return null;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      console.error("Auth validation failed:", msg);
      return msg;
    }
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(SESSION_KEY);
    setSession(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user: session?.user ?? null,
        credential: session?.credential ?? null,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
