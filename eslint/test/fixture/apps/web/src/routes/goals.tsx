// Caso: rota por arquivo do TanStack Router, com o componente no mesmo arquivo, passa no
// `react-refresh/only-export-components` (as fábricas de rota contam como HOC).
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/goals")({ component: GoalsRoute });

function GoalsRoute() {
  return null;
}
