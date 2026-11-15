// own-test: js/command-line-injection
// Fontes de requisição HTTP, amarradas ao tratador registrado no framework e não ao nome do
// parâmetro, com a revisão de 2026-11-14 contra Express.qll, NodeJSLib.qll, Koa.qll, Hapi.qll,
// Fastify.qll e Next.qll do CodeQL.
const cp = require("child_process");
const express = require("express");
const http = require("http");
const Koa = require("koa");
const Router = require("koa-router");
const Fastify = require("fastify");
const Hapi = require("@hapi/hapi");

const app = express();
const router = express.Router();

// Express: o tratador registrado no roteador, em qualquer forma de função.
app.get("/inline", (req, res) => {
  cp.exec(req.query.cmd); // $ Alert[js/command-line-injection]
});

router.post("/router", async function (request, res) {
  cp.exec(request.body.cmd); // $ Alert[js/command-line-injection]
});

app.use((err, req, res, next) => {
  cp.exec(req.params.cmd); // $ Alert[js/command-line-injection]
  // O primeiro parâmetro de quatro é o erro, não a requisição.
  cp.exec(err.query.cmd);
});

app.route("/chain").get((req, res) => {
  cp.exec(req.query.cmd); // $ Alert[js/command-line-injection]
});

app.enable("x-powered-by").get("/config-chain", (req, res) => {
  cp.exec(req.query.cmd); // $ Alert[js/command-line-injection]
});

function named(req, res) {
  cp.exec(req.query.cmd); // $ Alert[js/command-line-injection]
}
app.get("/named", named);

app.get("/headers", (req, res) => {
  cp.exec(req.get("x-cmd")); // $ Alert[js/command-line-injection]
  cp.exec(req.headers["x-cmd"]); // $ Alert[js/command-line-injection]
  // O CodeQL só modela a leitura de um cabeçalho, não o objeto inteiro.
  cp.exec(req.headers);
  // Sem modelo no Express.qll.
  cp.exec(req.baseUrl);
  cp.exec(req.subdomains);
  cp.exec(req.rawBody);
  cp.exec(req.signedCookies.session);
});

// Parâmetros de callbacks que não são tratador de rota não são requisição.
function unregistered(request) {
  cp.exec(request.query.cmd);
}

function others(rows, emitter, watcher, stream, map) {
  rows.map((r) => cp.exec(r.query));
  rows.map((r, i) => cp.exec(r.url + i));
  fetch("/data").then((r) => cp.exec(r.json()));
  emitter.on("change", (req, res) => cp.exec(req.query.cmd));
  watcher.on("change", (f) => cp.exec(f.path));
  stream.on("data", (file) => cp.exec(file.body));
  map.get("key", (item) => cp.exec(item.url));
}

// Servidor HTTP do Node: só `url`, `body` e a leitura de um cabeçalho são entrada.
http.createServer((req, res) => {
  cp.exec(req.url); // $ Alert[js/command-line-injection]
  cp.exec(req.headers.cookie); // $ Alert[js/command-line-injection]
  cp.exec(req.query.cmd);
  res.end();
});

const server = http.createServer();
server.on("request", function (req, res) {
  cp.exec(req.url); // $ Alert[js/command-line-injection]
});

// Koa: o contexto do tratador de `app.use` e do roteador do `koa-router`.
const koa = new Koa();
const koaRouter = new Router();
koa.use(async (ctx, next) => {
  cp.exec(ctx.query.cmd); // $ Alert[js/command-line-injection]
  cp.exec(ctx.request.body); // $ Alert[js/command-line-injection]
  // Sem modelo no Koa.qll.
  cp.exec(ctx.path);
  cp.exec(ctx.hostname);
  cp.exec(ctx.querystring);
});

koaRouter.get("/koa", (ctx) => {
  cp.exec(ctx.params.cmd); // $ Alert[js/command-line-injection]
});

// `context` de GraphQL ou de outra biblioteca, e `ctx` de um app que não é Koa.
function graphqlResolver(parent, args, context) {
  cp.exec(context.query.cmd);
}
const other = makeApp();
other.use(async (ctx) => {
  cp.exec(ctx.query.cmd);
});

// Fastify.
const fastify = Fastify();
fastify.get("/fastify", (request, reply) => {
  cp.exec(request.query.cmd); // $ Alert[js/command-line-injection]
});

// Hapi.
const hapi = Hapi.server({ port: 3000 });
hapi.route({
  method: "GET",
  path: "/hapi",
  handler: (request, h) => {
    cp.exec(request.query.cmd); // $ Alert[js/command-line-injection]
    cp.exec(request.url.path); // $ Alert[js/command-line-injection]
    cp.exec(request.raw);
    return "ok";
  },
});

// Next.js: `getServerSideProps` roda no servidor a cada requisição.
export async function getServerSideProps(context) {
  cp.exec(context.query.cmd); // $ Alert[js/command-line-injection]
  cp.exec(context.req.url); // $ Alert[js/command-line-injection]
  return { props: {} };
}

module.exports = { app, router, koa, koaRouter, fastify, hapi, server, unregistered, others };
