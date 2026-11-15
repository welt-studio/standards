// own-test: js/path-injection
// Sem o pacote importado, `open` e `puppeteer`-like não são sumidouros (js/path-injection), com a
// revisão de 2026-11-14 contra o TaintedPathCustomizations.qll e o open.model.json do CodeQL.
const express = require("express");

const app = express();

function open(target) {
  return target;
}

app.get("/open", (req, res) => {
  open(req.query.file);
  const document = { pdf: (options) => options, screenshot: (options) => options };
  document.pdf({ path: req.query.file });
  document.screenshot({ path: req.query.file });
  res.end();
});

module.exports = app;
