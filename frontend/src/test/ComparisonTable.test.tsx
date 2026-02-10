import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ComparisonTable } from "../components/ComparisonTable";
import type { TableData } from "../hooks/useTableStream";

const emptyTable: TableData = { title: null, columns: [], rows: [] };

const fullTable: TableData = {
  title: "Engagement WoW",
  columns: ["Dimension", "Previous", "Current", "Delta"],
  rows: [
    {
      dimension: "Mobile DAU",
      previous_value: "12,450",
      current_value: "11,500",
      delta: "-7.6%",
      is_top_contributor: true,
    },
    {
      dimension: "Web DAU",
      previous_value: "45,200",
      current_value: "44,800",
      delta: "-0.9%",
      is_top_contributor: false,
    },
    {
      dimension: "Desktop DAU",
      previous_value: "8,100",
      current_value: "8,500",
      delta: "+4.9%",
      is_top_contributor: false,
    },
  ],
};

describe("ComparisonTable", () => {
  it("empty table shows placeholder", () => {
    render(<ComparisonTable table={emptyTable} />);
    expect(
      screen.getByText("Data will appear here after analysis")
    ).toBeInTheDocument();
  });

  it("renders title", () => {
    render(<ComparisonTable table={fullTable} />);
    expect(screen.getByText("Engagement WoW")).toBeInTheDocument();
  });

  it("renders all rows", () => {
    const { container } = render(<ComparisonTable table={fullTable} />);
    const rows = container.querySelectorAll("tbody tr");
    expect(rows.length).toBe(3);
  });

  it("top contributor has red indicator", () => {
    const { container } = render(<ComparisonTable table={fullTable} />);
    // The red dot is a span with bg-red-500 class
    const redDots = container.querySelectorAll("span.bg-red-500");
    // Two: one in the row, one in the legend
    expect(redDots.length).toBeGreaterThanOrEqual(1);
  });

  it("negative delta shows red text", () => {
    const { container } = render(<ComparisonTable table={fullTable} />);
    const redCells = container.querySelectorAll(".text-red-400");
    expect(redCells.length).toBeGreaterThanOrEqual(1);
    // Check that one of them contains the delta
    const deltas = Array.from(redCells).map((el) => el.textContent);
    expect(deltas).toContain("-7.6%");
  });
});
