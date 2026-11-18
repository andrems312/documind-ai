import { render, screen } from "@testing-library/react";
import { AnswerContent } from "./answer-content";

describe("AnswerContent", () => {
  it("renders bold text and paragraphs", () => {
    render(<AnswerContent content="O prazo é de **24 meses**." />);
    expect(screen.getByText("24 meses").tagName).toBe("STRONG");
  });

  it("renders bullet lists", () => {
    render(<AnswerContent content={"Itens:\n\n- Primeiro\n- Segundo"} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("renders citation markers as source buttons", () => {
    render(<AnswerContent content="Conforme o contrato [1]." ranks={new Set([1])} onCite={() => {}} />);
    expect(screen.getByRole("button", { name: "Ver fonte 1" })).toBeInTheDocument();
  });

  it("disables citations whose rank is not valid", () => {
    render(<AnswerContent content="Texto [9]." ranks={new Set([1])} onCite={() => {}} />);
    expect(screen.getByRole("button", { name: "Ver fonte 9" })).toBeDisabled();
  });
});
