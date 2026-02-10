import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { LoginScreen } from "../components/LoginScreen";
import { AuthProvider } from "../hooks/useAuth";

// Mock jwt-decode (needed by AuthProvider)
vi.mock("jwt-decode", () => ({
  jwtDecode: vi.fn(),
}));

// Mock Google OAuth — capture callbacks for programmatic triggering
let capturedOnSuccess: ((res: any) => void) | null = null;
let capturedOnError: (() => void) | null = null;

vi.mock("@react-oauth/google", () => ({
  GoogleLogin: (props: any) => {
    capturedOnSuccess = props.onSuccess;
    capturedOnError = props.onError;
    return <div data-testid="google-login">GoogleLogin</div>;
  },
}));

vi.stubEnv("VITE_GOOGLE_CLIENT_ID", "test-client-id");

function renderLoginScreen() {
  return render(
    <AuthProvider>
      <LoginScreen />
    </AuthProvider>
  );
}

describe("LoginScreen", () => {
  beforeEach(() => {
    capturedOnSuccess = null;
    capturedOnError = null;
  });

  it("renders sign-in text", () => {
    renderLoginScreen();
    expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
  });

  it("renders GoogleLogin component", () => {
    renderLoginScreen();
    expect(screen.getByTestId("google-login")).toBeInTheDocument();
  });

  it("shows error on Google failure", () => {
    renderLoginScreen();
    act(() => {
      capturedOnError?.();
    });
    expect(
      screen.getByText("Google Sign-In failed. Please try again.")
    ).toBeInTheDocument();
  });

  it("shows error when no credential", () => {
    renderLoginScreen();
    act(() => {
      capturedOnSuccess?.({});
    });
    expect(
      screen.getByText("No credential received. Try disabling popup blockers.")
    ).toBeInTheDocument();
  });
});
