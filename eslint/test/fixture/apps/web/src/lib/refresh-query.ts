// Caso: `invalidateQueries` e `refetch` do TanStack Query sem `await` passam no
// `no-floating-promises`: os dois pegam o erro da query e não rejeitam.
import type { QueryClient, QueryObserver } from "@tanstack/query-core";

export function refresh(client: QueryClient, observer: QueryObserver): void {
  client.invalidateQueries({ queryKey: ["goals"] });
  observer.refetch();
}
