import type { CallStatus } from "../hooks/useVapi";

interface Props {
  callStatus: CallStatus;
  onClick: () => void;
}

export function MicButton({ callStatus, onClick }: Props) {
  const isActive = callStatus === "active";
  const isConnecting = callStatus === "connecting";

  return (
    <div className="relative flex items-center justify-center">
      {/* Pulse ring when active */}
      {isActive && (
        <div className="absolute h-20 w-20 rounded-full bg-red-500/30 animate-pulse-ring" />
      )}

      <button
        onClick={onClick}
        disabled={isConnecting}
        className={`
          relative z-10 flex h-16 w-16 items-center justify-center rounded-full
          transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
          focus:ring-offset-gray-950
          ${
            isActive
              ? "bg-red-600 hover:bg-red-700 focus:ring-red-500"
              : isConnecting
                ? "bg-yellow-600 cursor-wait"
                : "bg-emerald-600 hover:bg-emerald-700 focus:ring-emerald-500"
          }
        `}
      >
        {isActive ? (
          /* Stop icon */
          <svg className="h-7 w-7 text-white" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="6" width="12" height="12" rx="2" />
          </svg>
        ) : isConnecting ? (
          /* Spinner */
          <svg className="h-7 w-7 text-white animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
          </svg>
        ) : (
          /* Mic icon */
          <svg className="h-7 w-7 text-white" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 1a4 4 0 0 0-4 4v6a4 4 0 0 0 8 0V5a4 4 0 0 0-4-4Z" />
            <path d="M19 10v1a7 7 0 0 1-14 0v-1M12 19v4M8 23h8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        )}
      </button>

      <span className="absolute -bottom-7 text-xs text-gray-500 whitespace-nowrap">
        {isActive
          ? "Tap to end"
          : isConnecting
            ? "Connecting..."
            : "Tap to speak"}
      </span>
    </div>
  );
}
