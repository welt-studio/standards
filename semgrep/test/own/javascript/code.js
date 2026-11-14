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

module.exports = app;
