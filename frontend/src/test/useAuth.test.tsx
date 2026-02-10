import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider, useAuth } from "../hooks/useAuth";
import type { ReactNode } from "react";

// Mock jwt-decode
vi.mock("jwt-decode", () => ({
  jwtDecode: vi.fn(),
}));

// Set env var for tests
const TEST_CLIENT_ID = "test-client-id";
vi.stubEnv("VITE_GOOGLE_CLIENT_ID", TEST_CLIENT_ID);

import { jwtDecode } from "jwt-decode";
const mockJwtDecode = vi.mocked(jwtDecode);

function makeJwtPayload(overrides: Record<string, unknown> = {}) {
  return {
    iss: "https://accounts.google.com",
    aud: TEST_CLIENT_ID,
    exp: 9999999999,
    name: "Test User",
    email: "test@example.com",
    picture: "https://example.com/photo.jpg",
    ...overrides,
  };
}

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe("useAuth", () => {
  beforeEach(() => {
    sessionStorage.clear();
    mockJwtDecode.mockReset();
  });

  it("throws when used outside AuthProvider", () => {
    expect(() => {
      renderHook(() => useAuth());
    }).toThrow("useAuth must be used within AuthProvider");
  });

  it("login with valid JWT sets user", () => {
    mockJwtDecode.mockReturnValue(makeJwtPayload());
    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      const err = result.current.login("valid-credential");
      expect(err).toBeNull();
    });

    expect(result.current.user).toEqual({
      name: "Test User",
      email: "test@example.com",
      picture: "https://example.com/photo.jpg",
    });
    expect(result.current.credential).toBe("valid-credential");
  });

  it("login with wrong issuer returns error", () => {
    mockJwtDecode.mockReturnValue(makeJwtPayload({ iss: "evil.com" }));
    const { result } = renderHook(() => useAuth(), { wrapper });

    let err: string | null = null;
    act(() => {
      err = result.current.login("bad-iss-credential");
    });

    expect(err).toContain("issuer");
    expect(result.current.user).toBeNull();
  });

  it("login with wrong audience returns error", () => {
    mockJwtDecode.mockReturnValue(
      makeJwtPayload({ aud: "wrong-client-id" })
    );
    const { result } = renderHook(() => useAuth(), { wrapper });

    let err: string | null = null;
    act(() => {
      err = result.current.login("bad-aud-credential");
    });

    expect(err).toContain("audience");
    expect(result.current.user).toBeNull();
  });

  it("login with expired token returns error", () => {
    mockJwtDecode.mockReturnValue(makeJwtPayload({ exp: 1000000 }));
    const { result } = renderHook(() => useAuth(), { wrapper });

    let err: string | null = null;
    act(() => {
      err = result.current.login("expired-credential");
    });

    expect(err).toContain("expired");
    expect(result.current.user).toBeNull();
  });

  it("logout clears user", () => {
    mockJwtDecode.mockReturnValue(makeJwtPayload());
    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.login("valid-credential");
    });
    expect(result.current.user).not.toBeNull();

    act(() => {
      result.current.logout();
    });
    expect(result.current.user).toBeNull();
    expect(sessionStorage.getItem("v2d_auth")).toBeNull();
  });

  it("restores session on mount", () => {
    const session = {
      user: { name: "Stored User", email: "s@test.com", picture: "pic.jpg" },
      credential: "stored-cred",
      exp: 9999999999,
    };
    sessionStorage.setItem("v2d_auth", JSON.stringify(session));

    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.user).toEqual(session.user);
    expect(result.current.credential).toBe("stored-cred");
  });

  it("restores expired session clears user", () => {
    const session = {
      user: { name: "Expired User", email: "e@test.com", picture: "pic.jpg" },
      credential: "expired-cred",
      exp: 1000000, // Far in the past
    };
    sessionStorage.setItem("v2d_auth", JSON.stringify(session));

    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.user).toBeNull();
    expect(sessionStorage.getItem("v2d_auth")).toBeNull();
  });
});
