import { useCallback, useEffect, useRef, useState } from "react";
import Vapi from "@vapi-ai/web";

export type MessageRole = "user" | "assistant";
export interface Message {
  role: MessageRole;
  text: string;
  timestamp: number;
}

export type CallStatus = "idle" | "connecting" | "active" | "ended";
export type SpeechStatus = "idle" | "listening" | "thinking" | "speaking";

const VAPI_PUBLIC_KEY = import.meta.env.VITE_VAPI_PUBLIC_KEY || "";
const ASSISTANT_ID = import.meta.env.VITE_VAPI_ASSISTANT_ID || "";

export function useVapi() {
  const vapiRef = useRef<Vapi | null>(null);
  const [callStatus, setCallStatus] = useState<CallStatus>("idle");
  const [speechStatus, setSpeechStatus] = useState<SpeechStatus>("idle");
  const [messages, setMessages] = useState<Message[]>([]);
  const [callId, setCallId] = useState<string | null>(null);

  // Initialize VAPI client once
  useEffect(() => {
    if (!VAPI_PUBLIC_KEY) return;
    const vapi = new Vapi(VAPI_PUBLIC_KEY);
    vapiRef.current = vapi;

    vapi.on("call-start", () => {
      setCallStatus("active");
      setSpeechStatus("listening");
    });

    vapi.on("call-end", () => {
      setCallStatus("ended");
      setSpeechStatus("idle");
      // Reset to idle after a beat so UI can show "ended" briefly
      setTimeout(() => setCallStatus("idle"), 2000);
    });

    vapi.on("speech-start", () => {
      setSpeechStatus("speaking");
    });

    vapi.on("speech-end", () => {
      setSpeechStatus("listening");
    });

    vapi.on("message", (msg: any) => {
      // Capture conversation updates for the transcript
      if (msg.type === "conversation-update" && msg.conversation) {
        const conv: Message[] = msg.conversation
          .filter((m: any) => m.role === "user" || m.role === "assistant")
          .map((m: any) => ({
            role: m.role as MessageRole,
            text: m.content || "",
            timestamp: Date.now(),
          }));
        setMessages(conv);
      }

      // Capture transcript events for real-time partial updates
      if (msg.type === "transcript") {
        if (msg.transcriptType === "partial" && msg.role === "user") {
          setSpeechStatus("listening");
        }
        if (msg.transcriptType === "final" && msg.role === "user") {
          setSpeechStatus("thinking");
        }
      }
    });

    return () => {
      vapi.stop();
    };
  }, []);

  const startCall = useCallback(async () => {
    const vapi = vapiRef.current;
    if (!vapi || !ASSISTANT_ID) {
      console.error("VAPI not initialized or ASSISTANT_ID missing");
      return;
    }

    setCallStatus("connecting");
    setMessages([]);
    setSpeechStatus("idle");

    try {
      const call = await vapi.start(ASSISTANT_ID);
      setCallId(call?.id || null);
    } catch (err) {
      console.error("Failed to start call:", err);
      setCallStatus("idle");
    }
  }, []);

  const endCall = useCallback(() => {
    vapiRef.current?.stop();
  }, []);

  const toggleCall = useCallback(() => {
    if (callStatus === "idle" || callStatus === "ended") {
      startCall();
    } else {
      endCall();
    }
  }, [callStatus, startCall, endCall]);

  return {
    callStatus,
    speechStatus,
    messages,
    callId,
    toggleCall,
  };
}
