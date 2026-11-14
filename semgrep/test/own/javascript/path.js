// own-test: js/path-injection
// Injeção de caminho (js/path-injection), com a revisão de 2026-11-14 contra o
// TaintedPathCustomizations.qll do CodeQL.
const fs = require("fs");
const path = require("path");
const { resolve } = require("path");
const express = require("express");
const app = express();

app.get("/resolve", (req, res) => {
  // O `resolve` do `path` só monta o caminho: não lê nem grava arquivo.
  res.json({ file: resolve("/srv", req.query.file) });
});

app.get("/parse", (req, res) => {
  // O `name` do `path.parse` preserva o caminho contaminado.
  res.send(fs.readFileSync(path.parse(req.query.file).name)); // $ Alert[js/path-injection]
});

app.get("/storage", (req, res) => {
  // `readFile` de um objeto qualquer não é o do `fs`.
  const storage = { readFile: (name) => name };
  res.json({ file: storage.readFile(req.query.file) });
});

// Parâmetro chamado `r` ou `f` fora de uma rota não é requisição.
function load(rows, watcher) {
  rows.map((r) => fs.readFileSync(r.path));
  watcher.on("change", (f) => fs.readFileSync(f.path));
}

module.exports = { app, load };
