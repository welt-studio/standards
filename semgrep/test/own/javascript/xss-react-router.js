// own-test: js/xss
// Roteador do `react-router-dom` (js/xss): `useParams()` e o `params` do `useRouteMatch()` são fontes
// (ReactRouterSource, no React.qll do CodeQL); do `useLocation()` só o `search` e o `hash` (o
// `pathname` não é fonte).
import { useParams, useRouteMatch, useLocation } from "react-router-dom";

export function Profile() {
  const el = document.getElementById("out");
  const params = useParams();
  el.innerHTML = params.id; // $ Alert[js/xss]
  el.innerHTML = useRouteMatch().params.id; // $ Alert[js/xss]
  el.innerHTML = useLocation().search; // $ Alert[js/xss]
  el.innerHTML = useLocation().hash; // $ Alert[js/xss]
  el.innerHTML = useLocation().pathname;
  return null;
}
