// own-test: js/code-injection
// Injeção de código (js/code-injection), com a revisão de 2026-11-14 contra o
// CodeInjectionCustomizations.qll do CodeQL.
const express = require("express");
const app = express();

app.get("/methods", (req, res) => {
  // `eval` e `run` de um objeto qualquer não avaliam JavaScript (o CodeQL só aceita o `eval`
  // global e o do `window`).
  const math = { eval: (text) => text.length };
  const queue = { run: (text) => text.length };
  math.eval(req.query.expr);
  queue.run(req.query.job);
  res.end();
});

app.get("/encoded", (req, res) => {
  // `encodeURIComponent` não limpa para código: o CodeQL propaga a contaminação por ele.
  eval("f('" + encodeURIComponent(req.query.arg) + "')"); // $ Alert[js/code-injection]
  res.end();
});

app.get("/no-equivalent", (req, res) => {
  // Bibliotecas que o CodeQL não modela como execução de código: vm2, safer-eval, jQuery,
  // Electron, Puppeteer, Vue, ejs.compile e eta.compile.
  const { VM, NodeVM } = require("vm2");
  const saferEval = require("safer-eval");
  const ejs = require("ejs");
  const eta = require("eta");
  new VM().run(req.query.code);
  new NodeVM().run(req.query.code);
  saferEval(req.query.code);
  $.globalEval(req.query.code);
  jQuery.globalEval(req.query.code);
  win.webContents.executeJavaScript(req.query.code);
  page.evaluate(req.query.code);
  page.addScriptTag({ content: req.query.code });
  new Vue({ template: req.query.code });
  Vue.compile(req.query.code);
  ejs.compile(req.query.code);
  eta.compile(req.query.code);
  res.end();
});

app.get("/globals", (req, res) => {
  // `eval` e os que o CodeQL acha pelo objeto global (`globalVarRef`).
  eval(req.query.a); // $ Alert[js/code-injection]
  window.eval(req.query.a); // $ Alert[js/code-injection]
  self.eval(req.query.a); // $ Alert[js/code-injection]
  globalThis.eval(req.query.a); // $ Alert[js/code-injection]
  execScript(req.query.a); // $ Alert[js/code-injection]
  executeJavaScript(req.query.a); // $ Alert[js/code-injection]
  new Function("x", req.query.a); // $ Alert[js/code-injection]
  Function(req.query.a, "return 1"); // $ Alert[js/code-injection]
  setTimeout(req.query.a, 10); // $ Alert[js/code-injection]
  res.end();
});

app.get("/vm", (req, res) => {
  // Só o módulo `vm`: o mesmo nome em outro objeto não executa código.
  const vm = require("vm");
  const nodeVm = require("node:vm");
  const sandbox = { runInNewContext: (text) => text, Script: class {} };
  vm.runInNewContext(req.query.a); // $ Alert[js/code-injection]
  new vm.Script(req.query.a); // $ Alert[js/code-injection]
  new vm.SourceTextModule(req.query.a); // $ Alert[js/code-injection]
  nodeVm.runInThisContext(req.query.a); // $ Alert[js/code-injection]
  sandbox.runInNewContext(req.query.a);
  new sandbox.Script(req.query.a);
  res.end();
});

app.get("/templates", (req, res) => {
  // `whiskers.render` e `node-serialize` executam o texto; `webix.exec` e o `template` do `ui` também.
  const whiskers = require("whiskers");
  const { unserialize } = require("node-serialize");
  const serialize = require("node-serialize");
  whiskers.render(req.query.a); // $ Alert[js/code-injection]
  unserialize(req.query.a); // $ Alert[js/code-injection]
  serialize.unserialize(req.query.a); // $ Alert[js/code-injection]
  webix.exec(req.query.a); // $ Alert[js/code-injection]
  webix.ui({ template: req.query.a }); // $ Alert[js/code-injection]
  webix.ui(req.query.a);
  const script = document.createElement("script");
  script.textContent = req.query.a; // $ Alert[js/code-injection]
  const note = document.createElement("p");
  note.textContent = req.query.a;
  res.end();
});

app.get("/payload", () => {
  // Só os campos do `context.payload` que o CodeQL marca.
  const github = require("@actions/github");
  eval(github.context.payload.issue.title); // $ Alert[js/code-injection]
  eval(github.context.payload.sender.login);
  eval(github.context.payload.repository.full_name);
});

angular.module("app", []).controller("Main", function ($scope, $rootScope, $compile) {
  // O `$scope` e o `$rootScope` que o AngularJS injeta (e a variável que os guarda): outro
  // objeto com o mesmo método não interpreta expressão.
  const alias = $scope;
  const plain = { $eval: (text) => text, $apply: (text) => text };
  $scope.$eval(location.search); // $ Alert[js/code-injection]
  alias.$apply(location.search); // $ Alert[js/code-injection]
  $rootScope.$watch(location.search); // $ Alert[js/code-injection]
  $compile(location.search); // $ Alert[js/code-injection]
  plain.$eval(location.search);
  plain.$apply(location.search);
});

// `pathname` não é fonte de injeção de código (o CodeQL só marca hash, search, href, URL...).
eval(location.pathname);
eval(window.location.pathname);
eval(document.location.pathname);
eval(window.location.href); // $ Alert[js/code-injection]

module.exports = app;
