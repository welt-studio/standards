// own-test: js/xss-through-dom
// XSS através do DOM (js/xss-through-dom), com a revisão de 2026-11-15 contra o
// XssThroughDomCustomizations.qll do CodeQL: as fontes são leituras do DOM (e só a leitura), o
// receptor do jQuery é jQuery, e o `src` lido não vai para um sumidouro de endereço.
import { Formik } from "formik";

// A escrita da propriedade não é leitura (`el.textContent = ...`, `+=`).
function setStatus(panel, message) {
  panel.textContent = message;
  panel.value = "";
  panel.textContent += " ok";
  document.body.innerHTML = "<p>pronto</p>";
}

// Uma leitura chega ao HTML.
function copyField(form, box) {
  box.innerHTML = form.value; // $ Alert[js/xss-through-dom]
  box.innerHTML = form.textContent; // $ Alert[js/xss-through-dom]
  box.innerHTML = form.name; // $ Alert[js/xss-through-dom]
  box.innerHTML = form.getAttribute("data-label"); // $ Alert[js/xss-through-dom]
  box.innerHTML = form.getAttribute("aria-label"); // $ Alert[js/xss-through-dom]
  box.innerHTML = form.getAttribute("id");
  box.innerHTML = form.getAttribute("href");
}

// jQuery: o receptor é jQuery, o nome é um dos do CodeQL e o argumento é literal.
function readJquery(box) {
  $("#out").html($("#field").val()); // $ Alert[js/xss-through-dom]
  $("#out").html($("#field").text()); // $ Alert[js/xss-through-dom]
  $("#out").html($("#field").attr("data-note")); // $ Alert[js/xss-through-dom]
  $("#out").html($("#field").prop("value")); // $ Alert[js/xss-through-dom]
  $("#out").html($("#field").attr("id"));
  $("#out").html($("#field").prop("checked"));
  $("#out").html($("#field").attr("data-note", "fixo"));
  const field = $("#field");
  $("#out").html(field.find(".part").first().val()); // $ Alert[js/xss-through-dom]
}
async function readFetch(box) {
  const response = await fetch("/api/note");
  box.innerHTML = await response.text();
  const copy = response.clone();
  box.innerHTML = await copy.text();
}

// O sumidouro dentro do receptor de uma fonte é parte da fonte.
function readFromItem(item) {
  const theme = jQuery(item).attr("data-theme");
  const other = jQuery(item).text();
  return theme + other;
}

// O `$` de uma função local não é o jQuery.
function lookups(form, box) {
  const $ = (id) => document.getElementById(id);
  $(form.value).className = "ativo";
  box.className = $("fixo").className;
}

// O receptor encadeado: `find`, `filter` e outros métodos devolvem jQuery.
function appendChain(form) {
  const list = $("#list");
  list.find("li").filter(".novo").append(form.value); // $ Alert[js/xss-through-dom]
  document.body.append(form.value);
}

// Navegação e endereço: o texto lido vai a `location`, mas o `src` lido não.
function navigate(form, image, redirect) {
  const target = form.getAttribute("data-redirect");
  window.location.replace(target); // $ Alert[js/xss-through-dom]
  const link = document.createElement("a");
  link.href = form.value; // $ Alert[js/xss-through-dom]
  link.href = image.src;
  window.location.replace(image.src);
  const config = { href: "" };
  config.href = form.value;
}

// O CodeQL só propaga o dado pelos construtores que modela: `new Swiper(...)` não leva o valor, e
// a conta numérica também não.
function counter(form, box) {
  const slider = new Swiper(form, { speed: form.getAttribute("data-speed") });
  box.innerHTML = slider.realIndex + 1;
  box.innerHTML = form.value - 1;
  box.innerHTML = new TypeError(form.value); // $ Alert[js/xss-through-dom]
}

// Formik: o import de `formik` e o JSX `<Formik>`; um objeto qualquer com `onSubmit` não.
const handlers = {
  onSubmit: (values) => {
    document.body.innerHTML = values.title;
  },
};
const Page = () => (
  <Formik
    validate={(values) => {
      document.body.innerHTML = values.title; // $ Alert[js/xss-through-dom]
    }}
    onSubmit={(values) => {
      document.body.innerHTML = values.body; // $ Alert[js/xss-through-dom]
    }}
  />
);

// Sanitizadores e guardas.
function guarded(form, box) {
  box.innerHTML = encodeURIComponent(form.value);
  if (typeof form.value === "number") {
    box.innerHTML = form.value;
  }
  $("#a" + form.value).show();
}

// `name` de um objeto qualquer não é texto do DOM; o de um campo do formulário é.
function nameField(model) {
  const link = document.createElement("a");
  link.href = model.name;
  const field = document.getElementById("field");
  document.getElementById("out").innerHTML = field.name; // $ Alert[js/xss-through-dom]
}
