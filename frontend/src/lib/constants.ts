/** Limite exibido e checado no cliente para feedback imediato; o backend valida de novo. */
export const MAX_UPLOAD_MB = 25;
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;

/** Mesma frase usada pelo backend (app/ai/guards.py) quando não há base nos documentos. */
export const NO_ANSWER = "Não encontrei essa informação nos documentos selecionados.";
