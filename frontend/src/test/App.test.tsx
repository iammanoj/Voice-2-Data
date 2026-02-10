import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "../App";

// Mock jwt-decode
vi.mock("jwt-decode", () => ({
  jwtDecode: vi.fn(),
}));

// Mock @react-oauth/google
vi.mock("@react-oauth/google", () => ({
  GoogleLogin: (props: any) => (
    <div data-testid="google-login">GoogleLogin</div>
  ),
}));

// Mock useVapi hook to avoid Vapi SDK initialization
vi.mock("../hooks/useVapi", () => ({
  useVapi: () => ({
    callStatus: "idle",
    speechStatus: "idle",
    messages: [],
    callId: null,
    toggleCall: vi.fn(),
  }),
}));

// Mock useTableStream hook
vi.mock("../hooks/useTableStream", () => ({
  useTableStream: () => ({
    title: null,
    columns: [],
    rows: [],
  }),
}));

vi.stubEnv("VITE_GOOGLE_CLIENT_ID", "test-client-id");

describe("App", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("no user shows LoginScreen", () => {
    render(<App />);
    expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
  });

  it("with user shows MainApp", () => {
    const session = {
      user: { name: "Test User", email: "t@test.com", picture: "pic.jpg" },
      credential: "fake-cred",
      exp: 9999999999,
    };
    sessionStorage.setItem("v2d_auth", JSON.stringify(session));

    render(<App />);
    expect(screen.getByText("Voice-to-Data")).toBeInTheDocument();
    expect(screen.getByText("Sign out")).toBeInTheDocument();
  });

  it("sign out returns to LoginScreen", () => {
    const session = {
      user: { name: "Test User", email: "t@test.com", picture: "pic.jpg" },
      credential: "fake-cred",
      exp: 9999999999,
    };
    sessionStorage.setItem("v2d_auth", JSON.stringify(session));

    render(<App />);
    expect(screen.getByText("Voice-to-Data")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Sign out"));
    expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
  });
});
