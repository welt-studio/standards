// own-test: js/xss
// Servidor Express: escrita que não é DOM nem navegação (js/xss), com a revisão de 2026-11-14.
const express = require("express");
const app = express();

app.post("/profile", (req, res) => {
  // `location` de um objeto do domínio não é a navegação do navegador.
  const user = { name: "a" };
  user.location = req.body.location;
  process.stdout.write(req.body.name);
  res.json(user);
});

module.exports = app;
