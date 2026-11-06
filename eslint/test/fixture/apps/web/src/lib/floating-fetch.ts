// Caso: outra promise solta continua reprovando no `no-floating-promises`.
export function load(): void {
  fetch("/api/goals");
}
