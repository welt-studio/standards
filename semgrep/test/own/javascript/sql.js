// own-test: js/sql-injection
// Injeção de SQL e NoSQL (js/sql-injection), com a revisão de 2026-11-14 contra o
// SqlInjectionCustomizations.qll e o NosqlInjectionCustomizations.qll do CodeQL.
const express = require("express");
const mysql = require("mysql");
const mongoose = require("mongoose");
const _ = require("lodash");

const app = express();
const connection = mysql.createConnection({});
const User = mongoose.model("User", new mongoose.Schema({ name: String }));

app.get("/cache", (req, res) => {
  // `get` e `query` de objetos que não são banco de dados.
  const cache = new Map();
  const platform = { query: (text) => text };
  cache.get(req.query.key);
  platform.query(req.query.q);
  res.end();
});

app.get("/user/:id", async (req, res) => {
  // O parâmetro de rota é texto, não objeto: não injeta operador do MongoDB.
  res.json(await User.findOne({ _id: req.params.id }));
});

app.get("/escape", (req, res) => {
  // Escape de HTML não é escape de SQL: só o `escape` do mysql limpa.
  connection.query("select * from t where name = '" + _.escape(req.query.name) + "'"); // $ Alert[js/sql-injection]
  res.end();
});

module.exports = app;
