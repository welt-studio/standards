// own-test: js/xss
// Roteador e `<Link>` do Next.js (js/xss): o roteador é o do `next/router` (NextJS::nextRouter, no
// Next.qll do CodeQL), e o `href` do `next/link` é sumidouro de URL (ReactAttributeWriteUrlSink).
import { useRouter, withRouter } from "next/router";
import Link from "next/link";

export function Page() {
  const router = useRouter();
  const el = document.getElementById("out");
  el.innerHTML = router.query.name; // $ Alert[js/xss]
  el.innerHTML = useRouter().query.title; // $ Alert[js/xss]
  router.push(window.name); // $ Alert[js/xss]
  return <Link href={window.name}>voltar</Link>; // $ Alert[js/xss]
}

// Página embrulhada por `withRouter`: o roteador chega na prop `router`.
function Wrapped({ router }) {
  const el = document.getElementById("out");
  el.innerHTML = router.query.name; // $ Alert[js/xss]
  router.push(router.query.next); // $ Alert[js/xss]
  return null;
}
export const WrappedPage = withRouter(Wrapped);

// `useSearchParams` e as props `searchParams`/`params` não são fontes do CodeQL.
export function Search(props) {
  const el = document.getElementById("out");
  el.innerHTML = props.searchParams.q;
  el.innerHTML = props.params.slug;
  return null;
}
