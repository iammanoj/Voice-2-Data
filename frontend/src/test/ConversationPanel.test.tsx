import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ConversationPanel } from "../components/ConversationPanel";
import type { Message } from "../hooks/useVapi";

describe("ConversationPanel", () => {
  it("empty messages shows placeholder", () => {
    render(<ConversationPanel messages={[]} />);
    expect(
      screen.getByText("Tap the mic to start a conversation")
    ).toBeInTheDocument();
  });

  it("renders user message", () => {
    const messages: Message[] = [
      { role: "user", text: "hello", timestamp: 0 },
    ];
    render(<ConversationPanel messages={messages} />);
    expect(screen.getByText("You")).toBeInTheDocument();
    expect(screen.getByText("hello")).toBeInTheDocument();
  });

  it("renders assistant message", () => {
    const messages: Message[] = [
      { role: "assistant", text: "hi there", timestamp: 0 },
    ];
    render(<ConversationPanel messages={messages} />);
    expect(screen.getByText("Analyst")).toBeInTheDocument();
    expect(screen.getByText("hi there")).toBeInTheDocument();
  });
});
