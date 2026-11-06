// Caso: arquivo de rota que exporta outra coisa além do `Route` continua reprovando no
// `react-refresh/only-export-components`.
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/goal")({ component: GoalRoute });

export function formatGoal(value: number): string {
  return value.toFixed(2);
}

function GoalRoute() {
  return null;
}
