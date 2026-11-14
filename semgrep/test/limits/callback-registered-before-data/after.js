const cp = require("child_process");

const { Command } = require("commander");

function handler(req) {
  const program = new Command();
  program.parse(req.body.args);
  program.command("run <script>").action((script) => {
    cp.exec(script);
  });
}
