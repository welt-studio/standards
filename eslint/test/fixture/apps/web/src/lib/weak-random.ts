// Caso: valor de segurança gerado com `Math.random()`, que é previsível. Reprova o
// `no-restricted-properties`; o `crypto.getRandomValues()` passa.
export function weakToken(): string {
  return Math.random().toString(36).slice(2);
}

export function strongToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}
