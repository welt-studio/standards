// own-test: js/path-injection
// Injeção de caminho (js/path-injection), com a revisão de 2026-11-14 contra o
// TaintedPathCustomizations.qll do CodeQL.
const fs = require("fs");
const path = require("node:path");
const { resolve } = require("path");
const express = require("express");
const resolvePackage = require("resolve");
const sanitizeFilename = require("sanitize-filename");
const slugify = require("slugify");
const ejs = require("ejs");
const del = require("del");
const rimraf = require("rimraf");
const execa = require("execa");
const childProcess = require("child_process");
const app = express();

app.get("/resolve", (req, res) => {
  // O `resolve` do `path` só monta o caminho: não lê nem grava arquivo.
  res.json({ file: resolve("/srv", req.query.file) });
  // O do pacote `resolve` procura o módulo no disco.
  res.json({ file: resolvePackage(req.query.file) }); // $ Alert[js/path-injection]
  res.json({ file: resolvePackage.sync(req.query.file) }); // $ Alert[js/path-injection]
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

app.get("/render", (req, res) => {
  // `render` de um motor de modelos não é o da resposta do Express.
  res.send(ejs.render(req.query.template));
  res.render(req.query.view); // $ Alert[js/path-injection]
});

app.get("/send", (req, res) => {
  res.sendFile(req.query.file); // $ Alert[js/path-injection]
  res.sendFile(req.query.file, { root: "/srv/public" });
  res.download(req.query.file); // $ Alert[js/path-injection]
});

// `res` fora de um tratador registrado não é a resposta do Express.
function reply(response, name) {
  response.render(name);
  response.sendFile(name);
}

app.get("/names", (req, res) => {
  // Funções com nome de biblioteca, sem o módulo importado, não são sumidouros.
  const touch = (file) => file;
  const trash = (file) => file;
  const opn = (file) => file;
  const tmp = { file: (name) => name };
  const server = { static: (dir) => dir };
  touch(req.query.file);
  trash(req.query.file);
  opn(req.query.file);
  tmp.file(req.query.file);
  server.static(req.query.file);
  res.end();
});

app.get("/libraries", (req, res) => {
  // `del` e `execa` direto (o primeiro argumento) e o `execFile` não são sumidouros de caminho;
  // `rimraf` é.
  del(req.query.file);
  execa(req.query.file);
  childProcess.execFile(req.query.file);
  rimraf(req.query.file); // $ Alert[js/path-injection]
  childProcess.exec("ls", { cwd: req.query.dir }); // $ Alert[js/path-injection]
});

app.get("/sanitized", (req, res) => {
  // Só as bibliotecas de nome de arquivo importadas limpam o caminho.
  fs.readFileSync(sanitizeFilename(req.query.file));
  fs.readFileSync(slugify(req.query.file));
});

// Parâmetro chamado `r` ou `f` fora de uma rota não é requisição.
function load(rows, watcher) {
  rows.map((r) => fs.readFileSync(r.path));
  watcher.on("change", (f) => fs.readFileSync(f.path));
}

module.exports = { app, load };
