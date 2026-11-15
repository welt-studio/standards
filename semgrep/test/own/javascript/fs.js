// own-test: js/path-injection
// O módulo fs é o ligado pelo `require` ou pelo `import` (fs, fs-extra, graceful-fs, mz/fs,
// original-fs, fs/promises e `node:`), como o `FS::moduleMember` do NodeJSLib.qll do CodeQL, e não
// o objeto que tem o nome `fs`, `promises`, `fileSystem`, `jetpack` ou `vfs`.
const express = require("express");
const fs = require("fs");
const fse = require("fs-extra");
const nodeFs = require("node:fs");
const { readFile } = require("fs");
const { readFile: readAsync } = require("fs/promises");
const fsp = require("fs").promises;
const util = require("util");
const app = express();

app.get("/modules", (req, res) => {
  const file = req.query.file;
  fs.readFileSync(file); // $ Alert[js/path-injection]
  fse.remove(file); // $ Alert[js/path-injection]
  nodeFs.readFileSync(file); // $ Alert[js/path-injection]
  readFile(file); // $ Alert[js/path-injection]
  readAsync(file); // $ Alert[js/path-injection]
  fsp.readFile(file); // $ Alert[js/path-injection]
  fs.promises.readFile(file); // $ Alert[js/path-injection]
  util.promisify(fs.readFile)(file); // $ Alert[js/path-injection]
  // Origem e destino: os dois argumentos são caminho.
  fs.copyFileSync("a.txt", file); // $ Alert[js/path-injection]
  fs.renameSync(file, "b.txt"); // $ Alert[js/path-injection]
  // `readFile` não lê o segundo argumento como caminho.
  fs.readFileSync("a.txt", file);
});

app.get("/other-objects", (req, res) => {
  const file = req.query.file;
  // Objetos que só se chamam `fs`, `promises`, `fileSystem`, `jetpack` ou `vfs`.
  const jetpack = makeJetpack();
  const fileSystem = makeVirtualFs();
  const vfs = makeVirtualFs();
  const promises = new Map();
  jetpack.read(file);
  fileSystem.readFile(file);
  vfs.readFileSync(file);
  promises.readFile(file);
  other.fs.readFile(file);
});

module.exports = { app };
