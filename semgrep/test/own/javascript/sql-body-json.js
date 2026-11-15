// own-test: js/sql-injection
// `req.body` quando há outro parser além do `urlencoded` simples (js/sql-injection), com a revisão
// de 2026-11-14 contra o Express.qll do CodeQL (`bodyParser.producesUserControlledObjects`).
const express = require("express");
const bodyParser = require("body-parser");
const mongoose = require("mongoose");

const app = express();
const Invoice = mongoose.model("Invoice", new mongoose.Schema({ code: String }));

app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());

app.post("/invoices", async (req, res) => {
  // O `json` entrega objetos: o corpo volta a ser fonte.
  res.json(await Invoice.find({ code: req.body.code })); // $ Alert[js/sql-injection]
});

module.exports = app;
