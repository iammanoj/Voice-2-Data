import type { CallStatus, SpeechStatus } from "../hooks/useVapi";

interface Props {
  callStatus: CallStatus;
  speechStatus: SpeechStatus;
}

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  idle: { label: "Ready", color: "bg-gray-500" },
  connecting: { label: "Connecting...", color: "bg-yellow-500" },
  listening: { label: "Listening...", color: "bg-green-500" },
  thinking: { label: "Analyzing...", color: "bg-blue-500" },
  speaking: { label: "Speaking...", color: "bg-purple-500" },
  ended: { label: "Call ended", color: "bg-gray-500" },
};

export function StatusIndicator({ callStatus, speechStatus }: Props) {
  const key =
    callStatus === "active" ? speechStatus : callStatus;
  const { label, color } = STATUS_CONFIG[key] || STATUS_CONFIG.idle;

  return (
    <div className="flex items-center gap-2 text-sm text-gray-400">
      <span
        className={`h-2 w-2 rounded-full ${color} ${
          callStatus === "active" ? "animate-pulse" : ""
        }`}
      />
      {label}
    </div>
  );
}
