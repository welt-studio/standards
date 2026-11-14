// own-test: js/command-line-injection
// Injeção de comando (js/command-line-injection), com as revisões de 2026-11-14 contra o
// CommandInjectionCustomizations.qll e o IndirectCommandArgument.qll do CodeQL.
const cp = require("child_process");
const express = require("express");
const app = express();

app.get("/regex", (req, res) => {
  // `exec` de expressão regular não executa comando (o CodeQL só aceita o `exec` do ssh2).
  /^[a-z]+$/.exec(req.query.name);
  new RegExp("^[a-z]+$").exec(req.query.name);
  res.end();
});

app.get("/tagged", (req, res) => {
  // Modelo de texto com etiqueta que não é o `$` do execa: a interpolação não vira comando.
  const sql = (strings, ...values) => ({ strings, values });
  sql`select * from t where id = ${req.query.id}`;
  res.end();
});

app.get("/shell-script", (req, res) => {
  // Shell sem `-c`: o valor é argumento do script, não comando (IndirectCommandArgument.qll).
  cp.spawn("bash", ["script.sh", req.query.arg]);
  res.end();
});

app.get("/quote", (req, res) => {
  // `quote` de um objeto qualquer não é escape de shell: o CodeQL não tem sanitizador aqui.
  const db = { quote: (text) => text };
  cp.exec("ls " + db.quote(req.query.dir)); // $ Alert[js/command-line-injection]
  res.end();
});

// Parâmetro chamado `r` ou `e` fora de uma rota não é requisição.
function listAll(rows, emitter) {
  rows.map((r) => cp.exec("ls " + r.path));
  emitter.on("change", (e) => cp.exec("ping " + e.host));
}

module.exports = { app, listAll };
