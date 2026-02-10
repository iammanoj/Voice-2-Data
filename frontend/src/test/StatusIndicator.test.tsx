import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusIndicator } from "../components/StatusIndicator";

describe("StatusIndicator", () => {
  it("idle shows Ready", () => {
    render(<StatusIndicator callStatus="idle" speechStatus="idle" />);
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("active + listening shows Listening...", () => {
    render(<StatusIndicator callStatus="active" speechStatus="listening" />);
    expect(screen.getByText("Listening...")).toBeInTheDocument();
  });

  it("active + thinking shows Analyzing...", () => {
    render(<StatusIndicator callStatus="active" speechStatus="thinking" />);
    expect(screen.getByText("Analyzing...")).toBeInTheDocument();
  });

  it("connecting shows Connecting...", () => {
    render(<StatusIndicator callStatus="connecting" speechStatus="idle" />);
    expect(screen.getByText("Connecting...")).toBeInTheDocument();
  });
});
