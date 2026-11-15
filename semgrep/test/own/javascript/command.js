// own-test: js/command-line-injection
// Injeção de comando (js/command-line-injection), com as revisões de 2026-11-14 contra o
// CommandInjectionCustomizations.qll e o IndirectCommandArgument.qll do CodeQL.
const cp = require("child_process");
const express = require("express");
const app = express();

app.get("/regex", (req, res) => {
  // `exec` de expressão regular não executa comando (o CodeQL só aceita o `exec` do ssh2).
  /^[a-z]+$/.exec(req.query.name);
  new RegExp("^[a-z]+$").exec(req.query.name);
  res.end();
});

app.get("/tagged", (req, res) => {
  // Modelo de texto com etiqueta que não é o `$` do execa: a interpolação não vira comando.
  const sql = (strings, ...values) => ({ strings, values });
  sql`select * from t where id = ${req.query.id}`;
  res.end();
});

app.get("/shell-script", (req, res) => {
  // Shell sem `-c`: o valor é argumento do script, não comando (IndirectCommandArgument.qll).
  cp.spawn("bash", ["script.sh", req.query.arg]);
  res.end();
});

app.get("/quote", (req, res) => {
  // `quote` de um objeto qualquer não é escape de shell: o CodeQL não tem sanitizador aqui.
  const db = { quote: (text) => text };
  cp.exec("ls " + db.quote(req.query.dir)); // $ Alert[js/command-line-injection]
  res.end();
});

// Parâmetro chamado `r` ou `e` fora de uma rota não é requisição.
function listAll(rows, emitter) {
  rows.map((r) => cp.exec("ls " + r.path));
  emitter.on("change", (e) => cp.exec("ping " + e.host));
}

app.get("/receivers", (req, res) => {
  // `exec` sem o módulo `ssh2` (banco, objeto qualquer) e `execCommand` não executam comando.
  const db = { exec: (text) => text, execCommand: (text) => text };
  db.exec(req.query.sql);
  db.execCommand(req.query.sql);
  // Nomes soltos, sem `child_process`: a função é local, não o módulo.
  const exec = (text) => text;
  const spawn = (text) => text;
  exec("ls " + req.query.dir);
  spawn(req.query.dir);
  // Bibliotecas e membros que o CodeQL não modela como execução de comando.
  const shx = { exec: (text) => text };
  const shell = { exec: (text) => text };
  const cmd = { run: (text) => text };
  const execa = { command: (text) => text };
  shx.exec(req.query.dir);
  shell.exec(req.query.dir);
  cmd.run(req.query.dir);
  execa.command(req.query.dir);
  res.end();
});

app.get("/shells", (req, res) => {
  // Só `sh`/`bash` com `-c` e `cmd`/`cmd.exe` com `/c` entregam a lista como comando.
  cp.spawn("bash", ["-c", req.query.cmd]); // $ Alert[js/command-line-injection]
  cp.spawn("/bin/sh", ["-c", "echo", req.query.cmd]); // $ Alert[js/command-line-injection]
  cp.spawn("cmd.exe", ["/c", req.query.cmd]); // $ Alert[js/command-line-injection]
  cp.spawn("CMD", ["/C"].concat(req.query.cmd)); // $ Alert[js/command-line-injection]
  cp.execFile("sh", ["-c", req.query.cmd]); // $ Alert[js/command-line-injection]
  cp.spawn("zsh", ["-c", req.query.cmd]);
  cp.spawn("powershell", ["-Command", req.query.cmd]);
  cp.spawn("sh", ["/c", req.query.cmd]);
  cp.spawn("cmd", ["-c", req.query.cmd]);
  cp.spawn("bash", ["script.sh", req.query.arg]);
  res.end();
});

app.get("/shell-by-flow", (req, res) => {
  // O shell e o `-c` chegam por variável e por retorno de função: o fluxo os liga, uma vez só.
  const getShell = () => ({ cmd: "sh", arg: "-c" });
  const shellInfo = getShell();
  cp.spawn(shellInfo.cmd, [shellInfo.arg, req.query.cmd]); // $ Alert[js/command-line-injection]
  const interpreter = process.platform === "win32" ? "cmd.exe" : "/bin/sh";
  const flag = process.platform === "win32" ? "/c" : "-c";
  cp.spawn(interpreter, [flag, req.query.cmd]); // $ Alert[js/command-line-injection]
  // A lista montada por atribuição de índices: com o `-c` ela vira comando, sem ele não.
  const withFlag = [];
  withFlag[0] = "-c";
  withFlag[1] = req.query.cmd;
  cp.execFile("/bin/bash", withFlag); // $ Alert[js/command-line-injection]
  const withoutFlag = [];
  withoutFlag[0] = "script.sh";
  withoutFlag[1] = req.query.cmd;
  cp.execFile("/bin/bash", withoutFlag);
  res.end();
});

app.get("/modules", (req, res) => {
  const { exec: run } = require("child_process");
  const nodeCp = require("node:child_process");
  const mzCp = require("mz/child_process");
  run("a " + req.query.a); // $ Alert[js/command-line-injection]
  nodeCp.exec("b " + req.query.a); // $ Alert[js/command-line-injection]
  mzCp.exec("c " + req.query.a); // $ Alert[js/command-line-injection]
  nodeCp.spawn(req.query.a); // $ Alert[js/command-line-injection]
  res.end();
});

app.get("/libraries", (req, res) => {
  const sh = require("shelljs");
  const asyncShell = require("async-shelljs");
  const execAsync = require("async-execute");
  const crossSpawn = require("cross-spawn");
  const execaModule = require("execa");
  const execSh = require("exec-sh");
  sh.exec(req.query.a); // $ Alert[js/command-line-injection]
  sh.cmd(req.query.b, "-l"); // $ Alert[js/command-line-injection]
  sh.cmd("ls", req.query.b);
  asyncShell.asyncExec(req.query.c); // $ Alert[js/command-line-injection]
  execAsync(req.query.d); // $ Alert[js/command-line-injection]
  crossSpawn(req.query.e); // $ Alert[js/command-line-injection]
  crossSpawn.sync(req.query.f); // $ Alert[js/command-line-injection]
  execaModule.execaCommand(req.query.g); // $ Alert[js/command-line-injection]
  execaModule.command(req.query.h);
  execSh(req.query.i);
  res.end();
});

app.get("/templates", (req, res) => {
  const { $ } = require("execa");
  const html = (strings, ...values) => ({ strings, values });
  html`<p>${req.query.name}</p>`;
  $`${req.query.cmd} --help`; // $ Alert[js/command-line-injection]
  $`ls ${req.query.dir}`;
  res.end();
});

app.get("/sanitizers", (req, res) => {
  // O CodeQL não tem sanitizador de comando: nenhum destes limpa o valor.
  const shellEscape = (text) => text;
  const shellQuote = { quote: (text) => text };
  cp.exec("ls " + shellEscape(req.query.a)); // $ Alert[js/command-line-injection]
  cp.exec("ls " + shellQuote.quote(req.query.a)); // $ Alert[js/command-line-injection]
  res.end();
});

app.post("/upload", (req, res) => {
  // A lista de arquivos da requisição entra no `forEach`; o nome de cada um é do usuário.
  req.files.forEach((file) => {
    cp.exec("touch " + file.originalname); // $ Alert[js/command-line-injection]
  });
  res.end();
});

app.get("/promise", async (req, res) => {
  // O retorno do callback do `then` segue para o próximo `then` e para o `await`.
  Promise.resolve(req.query.cmd)
    .then((text) => text + " --help")
    .then((full) => cp.exec(full)); // $ Alert[js/command-line-injection]
  const built = await Promise.resolve(req.query.cmd).then((text) => "run " + text);
  cp.exec(built); // $ Alert[js/command-line-injection]
  res.end();
});

app.post("/arguments", (req, res) => {
  // O que as bibliotecas de linha de comando extraem de uma lista do usuário segue contaminado.
  const minimist = require("minimist");
  const yargs = require("yargs/yargs");
  const arg = require("arg");
  const commandLineArgs = require("command-line-args");
  cp.exec(minimist(req.body.args).cmd); // $ Alert[js/command-line-injection]
  cp.exec(yargs(req.body.args).parse().cmd); // $ Alert[js/command-line-injection]
  cp.exec(arg({ "--cmd": String }, { argv: req.body.args })["--cmd"]); // $ Alert[js/command-line-injection]
  cp.exec(commandLineArgs([{ name: "cmd" }], { argv: req.body.args }).cmd); // $ Alert[js/command-line-injection]
  res.end();
});

app.get("/payload", () => {
  // Só os campos do `context.payload` que o CodeQL marca (título, corpo, ref, mensagem...).
  const github = require("@actions/github");
  const payload = github.context.payload;
  cp.exec(`echo ${github.context.payload.pull_request.title}`); // $ Alert[js/command-line-injection]
  cp.exec(`echo ${github.context.payload.head_commit.author.name}`); // `head_commit` não é marcado
  cp.exec(`echo ${github.context.payload.sender.login}`);
  cp.exec(`echo ${github.context.payload.repository.name}`);
  cp.exec(`echo ${github.context.payload.commits[0].message}`); // $ Alert[js/command-line-injection]
  cp.exec(`echo ${payload.sender.login}`);
});

module.exports = { app, listAll };
