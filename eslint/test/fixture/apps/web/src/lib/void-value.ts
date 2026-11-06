// Caso: usar o resultado de uma expressão `void` como valor continua reprovando no
// `no-confusing-void-expression`.
function reset(): void {
  return;
}

export const result = reset();
