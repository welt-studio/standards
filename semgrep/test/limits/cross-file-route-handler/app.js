const app = require("express")();

// Controle: o tratador escrito na própria chamada é achado.
app.get("/inline/*", (req, res) => res.render(req.params[0]));

// O tratador de outro arquivo é registrado aqui.
const handler = require("./handler");
app.get("/views/*", handler);
