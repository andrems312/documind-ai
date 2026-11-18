import { render, screen } from "@testing-library/react";
import { UsageChart } from "./usage-chart";
import type { UsagePoint } from "@/types/api";

function makeData(tokens: number[]): UsagePoint[] {
  return tokens.map((t, i) => ({
    day: `2026-11-${String(i + 1).padStart(2, "0")}`,
    prompt_tokens: Math.floor(t / 2),
    completion_tokens: Math.ceil(t / 2),
    events: t > 0 ? 1 : 0,
  }));
}

describe("UsageChart", () => {
  it("renders one bar per data point", () => {
    const { container } = render(<UsageChart data={makeData([0, 10, 50, 0, 120])} />);
    expect(container.querySelectorAll("rect")).toHaveLength(5);
  });

  it("exposes an accessible description", () => {
    render(<UsageChart data={makeData([5, 5])} />);
    expect(screen.getByRole("img", { name: /tokens consumidos por dia/i })).toBeInTheDocument();
  });

  it("shows the peak total in the caption", () => {
    render(<UsageChart data={makeData([10, 999, 20])} />);
    expect(screen.getByText(/pico:/i).textContent).toContain("999");
  });
});
