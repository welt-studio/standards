// own-test: js/html-constructed-from-input
// HTML montado a partir de parâmetro de função de biblioteca (js/html-constructed-from-input), com a
// revisão de 2026-11-15 contra o UnsafeHtmlConstructionCustomizations.qll e o PackageExports.qll do
// CodeQL. O alerta fica no sumidouro de XSS que recebe a montagem, e a montagem tem de chegar a ele.
const { render } = require("@testing-library/react");
const { createRoot } = require("react-dom/client");
const marked = require("marked");
const mermaid = require("mermaid");
const snarkdown = require("snarkdown");
const MarkdownIt = require("markdown-it");
const md = new MarkdownIt({ html: true });
const safeMd = new MarkdownIt({ html: false });

// Montagem de HTML que chega ao sumidouro, direto ou por uma variável.
module.exports.card = function (title) {
  document.querySelector("#card").innerHTML = "<h2>" + title + "</h2>"; // $ Alert[js/html-constructed-from-input]
};
module.exports.cardVar = function (title) {
  const html = `<h2>${title}</h2>`;
  document.querySelector("#card").innerHTML = html; // $ Alert[js/html-constructed-from-input]
};
module.exports.cardJoin = function (title) {
  const html = ["<h2>", title, "</h2>"].join("");
  document.querySelector("#card").innerHTML = html; // $ Alert[js/html-constructed-from-input]
};

// O valor que vai direto ao sumidouro não é "HTML montado"; a montagem que não chega a um
// sumidouro também não alerta.
module.exports.rawValue = function (title) {
  document.querySelector("#card").innerHTML = title;
};
module.exports.onlyBuilds = function (title) {
  const html = "<h2>" + title + "</h2>";
  return html;
};
module.exports.plainText = function (title) {
  document.querySelector("#card").innerHTML = "titulo: " + title;
};

// Todos os parâmetros valem, não só o primeiro.
module.exports.pair = function (kind, label) {
  document.querySelector("#pair").innerHTML = "<i>" + label + "</i>"; // $ Alert[js/html-constructed-from-input]
};
module.exports.arrowThree = (a, b, c) => {
  document.querySelector("#third").innerHTML = "<p>" + c + "</p>"; // $ Alert[js/html-constructed-from-input]
};

// Nome que começa por `_` não é público.
module.exports._internal = function (title) {
  document.querySelector("#card").innerHTML = "<h2>" + title + "</h2>";
};

// Função que não é exportada: o parâmetro não é entrada de biblioteca.
function localCard(title) {
  document.querySelector("#card").innerHTML = "<h2>" + title + "</h2>";
}
localCard("fixo");

// Função declarada e exportada pelo nome.
function namedCard(title) {
  document.querySelector("#card").innerHTML = "<h2>" + title + "</h2>"; // $ Alert[js/html-constructed-from-input]
}
module.exports.namedCard = namedCard;

// O `render` de teste e de React não é Markdown: só o dos pacotes de Markdown amarrados ao import.
module.exports.mount = function (node) {
  render(node);
  createRoot(document.body).render(node);
  this.render(node);
};
module.exports.mdFromMarked = function (text) {
  const html = marked(text);
  document.querySelector("#doc").innerHTML = html; // $ Alert[js/html-constructed-from-input]
};
module.exports.mdFromSnarkdown = function (text) {
  document.querySelector("#doc").innerHTML = snarkdown(text); // $ Alert[js/html-constructed-from-input]
};
module.exports.mdFromMarkdownIt = function (text) {
  document.querySelector("#doc").innerHTML = md.render(text); // $ Alert[js/html-constructed-from-input]
};
module.exports.mdWithoutHtml = function (text) {
  document.querySelector("#doc").innerHTML = safeMd.render(text);
};
module.exports.mdFromMermaid = function (text) {
  document.querySelector("#doc").innerHTML = mermaid.render("graph", text); // $ Alert[js/html-constructed-from-input]
};
module.exports.mdNotRendered = function (text) {
  const html = marked(text);
  return html;
};
const pluginRenderer = { render(value) { return value; } };
module.exports.otherRender = function (text) {
  document.querySelector("#doc").innerHTML = pluginRenderer.render(text);
};

// XML: só o tipo que tem `xml`, e só quando o resultado vai ao DOM.
module.exports.xmlToDom = function (text) {
  const doc = new DOMParser().parseFromString(text, "text/xml");
  document.querySelector("#xml").appendChild(doc.documentElement); // $ Alert[js/html-constructed-from-input]
};
module.exports.htmlParse = function (text) {
  const doc = new DOMParser().parseFromString(text, "text/html");
  document.querySelector("#xml").appendChild(doc.documentElement);
};
module.exports.xmlNotUsed = function (text) {
  const doc = new DOMParser().parseFromString(text, "text/xml");
  return doc.documentElement.nodeName;
};

// Plugin do jQuery: `$.fn.extend` e `jQuery.extend($.fn, ...)`, todos os parâmetros.
$.fn.extend({
  badge: function (target, options) {
    $(target).html("<b>" + options.label + "</b>"); // $ Alert[js/html-constructed-from-input]
  },
});
jQuery.extend($.fn, {
  chip(target, options) {
    $(target).html("<b>" + options.text + "</b>"); // $ Alert[js/html-constructed-from-input]
  },
});

// Sanitizadores: `typeof` nas duas polaridades (exclui `string`), seletor, `this`, nome com html.
module.exports.byType = function (value) {
  if (typeof value === "number") {
    document.querySelector("#n").innerHTML = "<b>" + value + "</b>";
  }
  if (typeof value !== "number") {
    document.querySelector("#n").innerHTML = "<b>" + value + "</b>"; // $ Alert[js/html-constructed-from-input]
  } else {
    document.querySelector("#n").innerHTML = "<b>" + value + "</b>";
  }
  if (typeof value === "string") {
    document.querySelector("#n").innerHTML = "<b>" + value + "</b>"; // $ Alert[js/html-constructed-from-input]
  } else {
    document.querySelector("#n").innerHTML = "<b>" + value + "</b>";
  }
  if (typeof value !== "string") {
    document.querySelector("#n").innerHTML = "<b>" + value + "</b>";
  }
};
module.exports.bySelector = function (id) {
  $("#panel-" + id).show();
  const selector = "#item-" + id;
  $(selector).show();
};
module.exports.byName = function (options) {
  document.querySelector("#t").innerHTML = "<div>" + options.template + "</div>";
  document.querySelector("#t").innerHTML = "<div>" + options.bodyHtml + "</div>";
};
