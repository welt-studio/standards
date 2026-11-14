const cp = require("child_process");

function legacy(cmd) {
  cp.exec(cmd);
}

function handler(req) {
  legacy(req.body);
}
