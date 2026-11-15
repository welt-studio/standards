// own-test: js/xss
// `$X.query` de um objeto qualquer não é o roteador (js/xss): a fonte do Next.js exige o
// `next/router`, e o `useParams`/`useRouteMatch` exigem o `react-router-dom`.
import { useParams } from "some-router";
import { useSearchParams } from "next/navigation";

const el = document.getElementById("out");
const database = { query: "select 1" };
el.innerHTML = database.query;
el.innerHTML = database.query.name;
el.innerHTML = useParams().id;
el.innerHTML = useSearchParams().get("q");
el.innerHTML = $.urlParam("name");
