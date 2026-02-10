import { useEffect, useRef } from "react";
import type { Message } from "../hooks/useVapi";

interface Props {
  messages: Message[];
}

export function ConversationPanel({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-gray-600">
        <div className="text-center">
          <svg
            className="mx-auto mb-3 h-10 w-10 text-gray-700"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 0 1-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8Z"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p className="text-sm">Tap the mic to start a conversation</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 overflow-y-auto p-4">
      {messages.map((msg, i) => (
        <div
          key={i}
          className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`
              max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed
              ${
                msg.role === "user"
                  ? "bg-emerald-600/20 text-emerald-100 rounded-br-md"
                  : "bg-gray-800 text-gray-200 rounded-bl-md"
              }
            `}
          >
            <span className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-gray-500">
              {msg.role === "user" ? "You" : "Analyst"}
            </span>
            {msg.text}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
