const cp = require("child_process");
const { promisify } = require("util");

function legacy(cmd) {
  cp.exec(cmd);
}

function handler(req) {
  const run = promisify(legacy);
  run(req.body);
  const runInline = promisify((cmd, cb) => {
    cp.exec(cmd);
    cb(null);
  });
  runInline(req.body);
}
