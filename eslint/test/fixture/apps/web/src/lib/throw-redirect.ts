// Caso: `throw redirect(...)` do TanStack Router passa no `only-throw-error` (exceção do tipo
// `Redirect` do `@tanstack/router-core`), mesmo o `redirect` sendo um `Response`.
import { redirect } from "@tanstack/router-core";

export function toLogin(): never {
  throw redirect({ href: "https://auth.example.com/login" });
}
