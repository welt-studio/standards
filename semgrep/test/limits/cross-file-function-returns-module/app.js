const lib = require("./lib");

function local() {
  return require("fs");
}

// Controle: a função do próprio arquivo que devolve o `fs` é achada.
function control(req) {
  local().readFileSync(req.query.file);
}

function handler(req) {
  lib.pick(true).readFileSync(req.query.file);
}

module.exports = { control, handler };
