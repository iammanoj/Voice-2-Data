import { useState } from "react";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "../hooks/useAuth";

export function LoginScreen() {
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="flex h-screen items-center justify-center bg-gray-950">
      <div className="flex flex-col items-center gap-8">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600/20">
            <svg
              className="h-5 w-5 text-emerald-400"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M3 13h2v-2H3v2Zm4 4h2V7H7v10Zm4 4h2V3h-2v18Zm4-8h2v-2h-2v2Zm4-4h2v-2h-2v2Z" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-gray-100">
              Voice-to-Data
            </h1>
            <p className="text-xs text-gray-500">
              Executive Analytics Agent
            </p>
          </div>
        </div>

        {/* Sign-in card */}
        <div className="flex flex-col items-center gap-6 rounded-xl border border-gray-800/50 bg-gray-900/50 px-10 py-8">
          <p className="text-sm text-gray-400">Sign in to continue</p>
          <GoogleLogin
            onSuccess={(res) => {
              if (res.credential) {
                const err = login(res.credential);
                setError(err);
              } else {
                setError("No credential received. Try disabling popup blockers.");
              }
            }}
            onError={() => setError("Google Sign-In failed. Please try again.")}
            theme="filled_black"
            size="large"
            shape="pill"
          />
          {error && (
            <p className="text-xs text-red-400">{error}</p>
          )}
        </div>
      </div>
    </div>
  );
}
