// own-test: js/sql-injection
// Injeção de SQL e NoSQL (js/sql-injection), com a revisão de 2026-11-14 contra o
// SqlInjectionCustomizations.qll, o SQL.qll e o NosqlInjectionCustomizations.qll do CodeQL.
const express = require("express");
const mysql = require("mysql");
const mongoose = require("mongoose");
const pgPromise = require("pg-promise");
const Database = require("better-sqlite3");
const _ = require("lodash");
const he = require("he");

const app = express();
const connection = mysql.createConnection({});
const pool = mysql.createPool({});
const pgp = pgPromise();
const orders = pgp("postgres://localhost/orders");
const cache = new Database("cache.db");
const User = mongoose.model("User", new mongoose.Schema({ name: String }));

app.get("/cache", (req, res) => {
  // `get` e `query` de objetos que não são banco de dados.
  const memory = new Map();
  const platform = { query: (text) => text };
  const apiClient = { get: (url) => url };
  const params = new URLSearchParams();
  memory.get(req.query.key);
  platform.query(req.query.q);
  apiClient.get(req.query.url);
  params.get(req.query.name);
  res.end();
});

app.get("/names", (req, res) => {
  // Nome de variável com `orm`, `tx` ou `client` não faz da variável um banco.
  const form = { query: (text) => text, execute: (text) => text };
  const ctx = { prepare: (text) => text };
  const apiClient = { query: (text) => text };
  form.query(req.query.q);
  form.execute(req.query.q);
  ctx.prepare(req.query.q);
  apiClient.query(req.query.q);
  res.end();
});

app.get("/user/:id", async (req, res) => {
  // O parâmetro de rota é texto, não objeto: não injeta operador do MongoDB.
  res.json(await User.findOne({ _id: req.params.id }));
});

app.get("/user", async (req, res) => {
  // `req.query.nome` pode ser um objeto (`?nome[$ne]=`): vira operador do MongoDB.
  res.json(await User.find({ name: req.query.name })); // $ Alert[js/sql-injection]
});

app.get("/header", async (req, res) => {
  // Cabeçalho é sempre texto.
  res.json(await User.find({ name: req.headers["x-name"] }));
});

app.get("/parsed", async (req, res) => {
  // `JSON.parse` de um valor contaminado devolve um objeto controlado.
  const filter = JSON.parse(req.params.filter);
  res.json(await User.find(filter)); // $ Alert[js/sql-injection]
});

app.get("/registry", async (req, res) => {
  // Uma variável com `model` no nome não é um modelo do mongoose.
  const userModel = { find: (query) => query };
  userModel.find(req.query.filter);
  res.end();
});

app.get("/escape", (req, res) => {
  // Escape de HTML não é escape de SQL: só o `escape` do mysql limpa.
  connection.query("select * from t where name = '" + _.escape(req.query.name) + "'"); // $ Alert[js/sql-injection]
  connection.query("select * from t where name = '" + he.escape(req.query.name) + "'"); // $ Alert[js/sql-injection]
  connection.query("select * from t where name = " + mysql.escape(req.query.name));
  connection.query("select * from t where name = " + connection.escape(req.query.name));
  pool.query("select * from t where name = " + pool.escape(req.query.name));
  res.end();
});

app.get("/drivers", (req, res) => {
  // Só o objeto que o módulo importado cria é banco de dados.
  connection.query("select * from t where id = " + req.query.id); // $ Alert[js/sql-injection]
  pool.query({ sql: "select * from t where id = " + req.query.id }); // $ Alert[js/sql-injection]
  pool.getConnection((error, session) => {
    session.query("select * from t where id = " + req.query.id); // $ Alert[js/sql-injection]
  });
  orders.any("select * from t where id = " + req.query.id); // $ Alert[js/sql-injection]
  cache.exec("select * from t where id = " + req.query.id); // $ Alert[js/sql-injection]
  res.end();
});

module.exports = app;
