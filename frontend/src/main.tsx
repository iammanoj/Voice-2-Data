import React from "react";
import ReactDOM from "react-dom/client";
import { GoogleOAuthProvider } from "@react-oauth/google";
import App from "./App";
import "./index.css";

const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

function MissingClientId() {
  return (
    <div className="flex h-screen items-center justify-center bg-gray-950">
      <div className="rounded-xl border border-red-900/50 bg-red-950/30 px-8 py-6 text-center">
        <h2 className="text-lg font-semibold text-red-400">
          Missing VITE_GOOGLE_CLIENT_ID
        </h2>
        <p className="mt-2 text-sm text-gray-400">
          Add it to <code className="text-gray-300">frontend/.env</code> and
          restart the dev server.
        </p>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {clientId ? (
      <GoogleOAuthProvider clientId={clientId}>
        <App />
      </GoogleOAuthProvider>
    ) : (
      <MissingClientId />
    )}
  </React.StrictMode>
);
