// Caso: `throw notFound()` do TanStack Router passa no `only-throw-error` (tipo `NotFoundError` do
// `@tanstack/router-core`), mesmo não sendo um `Error`.
import { notFound } from "@tanstack/router-core";

export function missing(): never {
  throw notFound();
}
