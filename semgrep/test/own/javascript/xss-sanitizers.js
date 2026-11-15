// own-test: js/xss
// Sanitizadores de HTML (js/xss): o CodeQL (`HtmlSanitizerCall`, HtmlSanitizers.qll) reconhece os
// pacotes conhecidos pelo módulo e a função cujo nome tem `html` e `saniti|escape|strip`. Uma função
// do código que devolve o valor, mesmo com nome de `escape`/`encode`/`sanitize`/`stripTags`, e os
// guardas `typeof`, `isElement` e `.jquery` não limpam.
import he from "he";
import { escape as escapeText } from "validator";
const sanitizeHtml = require("sanitize-html");

const el = document.getElementById("out");
const text = window.name;

// Limpam: o módulo, o apelido da importação e o nome com `html`.
el.innerHTML = he.escape(text);
el.innerHTML = escapeText(text);
el.innerHTML = sanitizeHtml(text);
el.innerHTML = require("xss")(text);
el.innerHTML = utils.escapeHtml(text);
el.innerHTML = stripHtmlTags(text);

// Não limpam: funções do próprio código, sem `html` no nome, ou métodos de um objeto qualquer.
function escapeString(value) {
  return value;
}
function encodeHTML(value) {
  return value;
}
const codec = {
  encode: (value) => value,
  escape: (value) => value,
  sanitize: (value) => value,
  encodeForHTML: (value) => value,
  stripTags: (value) => value,
};
el.innerHTML = escapeString(text); // $ Alert[js/xss]
el.innerHTML = encodeHTML(text); // $ Alert[js/xss]
el.innerHTML = codec.encode(text); // $ Alert[js/xss]
el.innerHTML = codec.escape(text); // $ Alert[js/xss]
el.innerHTML = codec.sanitize(text); // $ Alert[js/xss]
el.innerHTML = codec.encodeForHTML(text); // $ Alert[js/xss]
el.innerHTML = codec.stripTags(text); // $ Alert[js/xss]

// `typeof`, `isElement` e `.jquery` não são guardas do CodeQL para XSS no DOM.
if (typeof text === "object") {
  el.innerHTML = text; // $ Alert[js/xss]
}
if (isElement(text)) {
  el.innerHTML = text; // $ Alert[js/xss]
}
if (text.jquery) {
  el.innerHTML = text; // $ Alert[js/xss]
}

// Sanitização opcional: o ramo sem sanitizar não conta, com `DOMPurify` ou com um sanitizador pelo nome.
el.innerHTML = enabled ? DOMPurify.sanitize(text) : text;
el.innerHTML = enabled ? escapeHtml(text) : text;
