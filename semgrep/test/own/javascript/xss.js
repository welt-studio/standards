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
const channel = new MessageChannel();
channel.port1.addEventListener("message", (event) => {
  el.innerHTML = event.data;
});

// O `message` da janela (`window`, `self` ou o escopo global) é fonte.
window.addEventListener("message", (event) => { el.innerHTML = event.data; }); // $ Alert[js/xss]
self.addEventListener("message", function (event) { el.innerHTML = event.data; }); // $ Alert[js/xss]
addEventListener("message", (event) => { el.innerHTML = event.data; }); // $ Alert[js/xss]

// `write` é do `document`; o `write` de um fluxo (`process.stdout`, `res`) não escreve HTML.
document.write(window.name); // $ Alert[js/xss]
window.document.write(window.name); // $ Alert[js/xss]
process.stdout.write(window.name);
channel.port1.write(window.name);

// Métodos do jQuery que leem a string como HTML valem para objeto jQuery, não para outro `append`.
$("#panel").append(window.name); // $ Alert[js/xss]
jQuery("#panel").html(window.name); // $ Alert[js/xss]
$("#panel").find(".item").before(window.name); // $ Alert[js/xss]
$("<a>").insertAfter(window.name); // $ Alert[js/xss]
const box = $("#box");
box.prepend(window.name); // $ Alert[js/xss]
box.html(() => window.name); // $ Alert[js/xss]
box.text(window.name);
document.body.append(window.name);
el.after(window.name);
el.replaceWith(window.name);

// O `$()` olha o prefixo: o que não começa por `<` é um seletor.
$("#panel-" + window.name);
$("<b>" + window.name + "</b>"); // $ Alert[js/xss]
$(window.name); // $ Alert[js/xss]

// `srcdoc`, `setHTMLUnsafe` e os atributos `on...` não são sumidouros do CodeQL.
const frame = document.createElement("iframe");
frame.srcdoc = window.name;
frame.setAttribute("srcdoc", window.name);
frame.setAttribute("onload", window.name);
el.setHTMLUnsafe(window.name);

// `location` de um objeto qualquer não é a navegação; a do `window`, da `document` e a solta são.
const profile = { location: "" };
profile.location = window.name;
profile.location.href = window.name;
profile.location.assign(window.name);
window.location.href = window.name; // $ Alert[js/xss]
document.location.replace(window.name); // $ Alert[js/xss]
location.assign(window.name); // $ Alert[js/xss]

// `parseHTML` do jQuery não é sumidouro do CodeQL.
$.parseHTML(window.name);

// O `this` do escopo global é o objeto global; dentro de uma função é outra coisa.
this.addEventListener("message", function (event) { el.innerHTML = event.data; }); // $ Alert[js/xss]
function widget() {
  this.addEventListener("message", function (event) { el.innerHTML = event.data; });
}

// d3: o `html` de uma seleção lê HTML; o `html` de outro objeto não.
d3.select("#out").html(window.name); // $ Alert[js/xss]
d3.selectAll(".row").attr("data-a", 1).html(() => window.name); // $ Alert[js/xss]
const table = { html: (text) => text };
table.html(window.name);

// AngularJS: o jqLite (`angular.element`, e o elemento da diretiva) é um objeto jQuery.
angular.element("<div>").html(window.name); // $ Alert[js/xss]
angular.module("app").directive("note", function () {
  return {
    link: function (scope, element) {
      element.html(window.name); // $ Alert[js/xss]
    },
  };
});

// `document.cookie` e o `pathname` não são fontes de XSS no DOM.
el.innerHTML = document.cookie;
el.innerHTML = window.location.pathname;
el.innerHTML = document.location.pathname;
