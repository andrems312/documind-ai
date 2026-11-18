import { render, screen } from "@testing-library/react";
import { AnalysisResult } from "./analysis-result";
import type { Analysis } from "@/types/api";

const analysis: Analysis = {
  id: "a1",
  type: "summary",
  document_ids: ["d1"],
  document_titles: ["Contrato"],
  title: "Resumo: Contrato",
  content: "Visão geral do contrato com **pontos** principais.",
  model: "openai/gpt-4.1-mini",
  created_at: "2026-11-18T10:00:00Z",
};

describe("AnalysisResult", () => {
  it("renders the title, type label and content", () => {
    render(<AnalysisResult analysis={analysis} />);
    expect(screen.getByText("Resumo: Contrato")).toBeInTheDocument();
    expect(screen.getByText("Resumo")).toBeInTheDocument();
    expect(screen.getByText("pontos").tagName).toBe("STRONG");
  });

  it("offers Markdown and PDF export", () => {
    render(<AnalysisResult analysis={analysis} />);
    expect(screen.getByRole("button", { name: /\.md/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /\.pdf/ })).toBeInTheDocument();
  });

  it("shows a delete button only when onDelete is provided", () => {
    const { rerender } = render(<AnalysisResult analysis={analysis} />);
    expect(screen.queryByRole("button", { name: /excluir an/i })).not.toBeInTheDocument();
    rerender(<AnalysisResult analysis={analysis} onDelete={() => {}} />);
    expect(screen.getByRole("button", { name: /excluir an/i })).toBeInTheDocument();
  });
});
