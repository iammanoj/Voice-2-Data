import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MicButton } from "../components/MicButton";

describe("MicButton", () => {
  it("idle shows Tap to speak", () => {
    render(<MicButton callStatus="idle" onClick={() => {}} />);
    expect(screen.getByText("Tap to speak")).toBeInTheDocument();
  });

  it("active shows Tap to end", () => {
    const { container } = render(
      <MicButton callStatus="active" onClick={() => {}} />
    );
    expect(screen.getByText("Tap to end")).toBeInTheDocument();
    // Button should have red background
    const button = container.querySelector("button");
    expect(button?.className).toContain("bg-red-600");
  });

  it("connecting shows Connecting and disabled", () => {
    const { container } = render(
      <MicButton callStatus="connecting" onClick={() => {}} />
    );
    expect(screen.getByText("Connecting...")).toBeInTheDocument();
    const button = container.querySelector("button");
    expect(button).toBeDisabled();
  });

  it("click calls onClick", () => {
    const onClick = vi.fn();
    const { container } = render(
      <MicButton callStatus="idle" onClick={onClick} />
    );
    const button = container.querySelector("button")!;
    fireEvent.click(button);
    expect(onClick).toHaveBeenCalledOnce();
  });
});
