// own-test: js/sql-injection
// Sem módulo de banco importado no arquivo, nada é consulta SQL (js/sql-injection), com a revisão de
// 2026-11-14 contra o SQL.qll do CodeQL.
const express = require("express");

const app = express();
const db = makeDatabase();
const session = makeSession();

app.get("/lookup", (req, res) => {
  // O nome `db` ou `session` não faz do objeto um banco, e `exec`, `prepare` e `get` também não
  // são consulta de um objeto qualquer.
  db.query("select * from t where id = " + req.query.id);
  db.exec(req.query.id);
  db.prepare(req.query.id);
  db.get(req.query.id);
  session.get(req.query.id);
  session.execute({ sql: req.query.id });
  res.end();
});

app.get("/documents", (req, res) => {
  // `collection` e `model` de um objeto qualquer: sem o driver do MongoDB importado, não é consulta.
  const registry = { collection: (name) => ({ find: (query) => [name, query] }) };
  const userModel = { find: (query) => query };
  registry.collection("users").find(req.query.filter);
  userModel.find(req.query.filter);
  res.end();
});

module.exports = app;
