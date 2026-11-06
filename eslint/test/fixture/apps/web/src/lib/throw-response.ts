// Caso: outro `throw` que não é `Error` continua reprovando no `only-throw-error`, inclusive um
// `Response` qualquer, que tem a mesma forma do `redirect` mas não é o tipo liberado.
export function fail(): never {
  throw new Response(null, { status: 302 });
}
