// own-test: js/sql-injection
// `req.body` de um parser que só entrega texto (js/sql-injection), com a revisão de 2026-11-14
// contra o Express.qll do CodeQL (`bodyParser.producesUserControlledObjects`).
const express = require("express");
const bodyParser = require("body-parser");
const mongoose = require("mongoose");

const app = express();
const Order = mongoose.model("Order", new mongoose.Schema({ code: String }));

app.use(bodyParser.urlencoded({ extended: false }));

app.post("/orders", async (req, res) => {
  // O `urlencoded` simples é o único parser: o corpo só tem texto.
  res.json(await Order.find({ code: req.body.code }));
});

module.exports = app;
