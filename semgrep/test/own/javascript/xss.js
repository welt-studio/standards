// own-test: js/xss
// XSS no DOM (js/xss), com a revisão de 2026-11-14 contra o DomBasedXssCustomizations.qll do
// CodeQL.
const el = document.getElementById("out");

// Um prefixo de texto não limpa para o `innerHTML`: só o `$()` do jQuery olha o prefixo.
el.innerHTML = "Welcome " + window.name; // $ Alert[js/xss]

// A função local que devolve o valor não é sanitizador, mesmo com o nome `sanitize`.
function sanitize(text) {
  return text;
}
el.innerHTML = sanitize(window.name); // $ Alert[js/xss]

// O `setHTML` sanitiza por padrão, e o `append` do DOM insere texto, não HTML.
el.setHTML(window.name);
el.append(window.name);

// O `pathname` não é fonte: o CodeQL só usa `hash`, `search` e `href` da URL.
el.innerHTML = location.pathname;

// Mensagem de um worker não vem de outra origem (o CodeQL só olha o `message` da janela).
const worker = new Worker("w.js");
worker.addEventListener("message", (event) => {
  el.innerHTML = event.data;
});
