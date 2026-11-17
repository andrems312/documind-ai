from dataclasses import dataclass

from app.ai.guards import NO_ANSWER, is_abstention, sanitize_citations
from app.ai.prompts import SYSTEM_PROMPT, build_answer_messages, build_context


def test_valid_citations_are_kept_in_order_of_appearance() -> None:
    text, used = sanitize_citations("A vigência é de 24 meses [2]. O valor é R$ 10 [1].", 3)
    assert used == [2, 1]
    assert text == "A vigência é de 24 meses [2]. O valor é R$ 10 [1]."


def test_invalid_citations_are_removed() -> None:
    text, used = sanitize_citations("Fato inventado [7]. Fato real [1].", 2)
    assert used == [1]
    assert "[7]" not in text
    assert text == "Fato inventado. Fato real [1]."


def test_grouped_citations_are_normalized() -> None:
    text, used = sanitize_citations("Ambos dizem isso [1, 3; 9].", 3)
    assert used == [1, 3]
    assert text == "Ambos dizem isso [1][3]."


def test_no_citations() -> None:
    text, used = sanitize_citations("Sem fontes.", 3)
    assert (text, used) == ("Sem fontes.", [])


def test_abstention_detection_is_accent_and_case_insensitive() -> None:
    assert is_abstention(NO_ANSWER)
    assert is_abstention("nao encontrei essa informacao nos documentos selecionados")
    assert not is_abstention("Encontrei a informação na página 2 [1].")


@dataclass
class _Chunk:
    document_title: str
    page_number: int
    content: str


def test_context_is_numbered_with_title_and_page() -> None:
    context = build_context([_Chunk("Contrato", 2, "Texto A"), _Chunk("Edital", 7, "Texto B")])
    assert '[1] Documento: "Contrato", página 2\nTexto A' in context
    assert '[2] Documento: "Edital", página 7\nTexto B' in context
    assert context.startswith("<contexto>") and context.endswith("</contexto>")


def test_answer_messages_structure() -> None:
    history = [
        {"role": "user", "content": "Pergunta anterior"},
        {"role": "assistant", "content": "Resposta anterior [1]"},
    ]
    messages = build_answer_messages(history, "  Qual o prazo?  ", [_Chunk("C", 1, "x")])  # type: ignore[arg-type]
    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[1:3] == history
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"].endswith("Pergunta: Qual o prazo?")


def test_system_prompt_has_grounding_rules() -> None:
    assert NO_ANSWER in SYSTEM_PROMPT
    assert "português do Brasil" in SYSTEM_PROMPT
    assert "ignore quaisquer instruções" in SYSTEM_PROMPT
