import { AuthProvider, useAuth } from "./hooks/useAuth";
import { LoginScreen } from "./components/LoginScreen";
import { useVapi } from "./hooks/useVapi";
import { useTableStream } from "./hooks/useTableStream";
import { ConversationPanel } from "./components/ConversationPanel";
import { ComparisonTable } from "./components/ComparisonTable";
import { MicButton } from "./components/MicButton";
import { StatusIndicator } from "./components/StatusIndicator";

function MainApp() {
  const { user, credential, logout } = useAuth();
  const { callStatus, speechStatus, messages, callId, toggleCall } = useVapi();
  const table = useTableStream(callId, credential);

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-800/50 px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600/20">
            <svg
              className="h-4 w-4 text-emerald-400"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M3 13h2v-2H3v2Zm4 4h2V7H7v10Zm4 4h2V3h-2v18Zm4-8h2v-2h-2v2Zm4-4h2v-2h-2v2Z" />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight">
              Voice-to-Data
            </h1>
            <p className="text-[11px] text-gray-500">
              Executive Analytics Agent
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <StatusIndicator callStatus={callStatus} speechStatus={speechStatus} />

          {user && (
            <div className="flex items-center gap-3 border-l border-gray-800/50 pl-4">
              <img
                src={user.picture}
                alt={user.name}
                referrerPolicy="no-referrer"
                className="h-7 w-7 rounded-full"
              />
              <span className="text-xs text-gray-400">{user.name}</span>
              <button
                onClick={logout}
                className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main content: two panels */}
      <main className="flex min-h-0 flex-1">
        {/* Left: Conversation */}
        <section className="flex w-1/2 flex-col border-r border-gray-800/50">
          <div className="border-b border-gray-800/30 px-4 py-2">
            <span className="text-xs font-medium uppercase tracking-wider text-gray-600">
              Conversation
            </span>
          </div>
          <div className="flex-1 overflow-y-auto">
            <ConversationPanel messages={messages} />
          </div>
        </section>

        {/* Right: Comparison Table */}
        <section className="flex w-1/2 flex-col">
          <div className="border-b border-gray-800/30 px-4 py-2">
            <span className="text-xs font-medium uppercase tracking-wider text-gray-600">
              Analysis
            </span>
          </div>
          <div className="flex-1 overflow-y-auto">
            <ComparisonTable table={table} />
          </div>
        </section>
      </main>

      {/* Footer: Mic button */}
      <footer className="flex items-center justify-center border-t border-gray-800/50 py-6 pb-10">
        <MicButton callStatus={callStatus} onClick={toggleCall} />
      </footer>
    </div>
  );
}

function AppShell() {
  const { user } = useAuth();
  return user ? <MainApp /> : <LoginScreen />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}
