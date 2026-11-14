const express = require("express");
const db = require("./from");

const app = express();

app.post("/find", (req, res) => {
  db.coll.find(req.body);
});
