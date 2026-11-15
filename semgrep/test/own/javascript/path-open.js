// own-test: js/path-injection
// `open`, Puppeteer e `node:path` (js/path-injection), com a revisão de 2026-11-14 contra o
// TaintedPathCustomizations.qll e o open.model.json do CodeQL.
import fs from "node:fs";
import path from "node:path";
import open, { openApp } from "open";
import puppeteer from "puppeteer";
import express from "express";

const app = express();
const kiosk = { open: (target) => target, pdf: (options) => options };

app.get("/open", (req, res) => {
  open(req.query.file); // $ Alert[js/path-injection]
  openApp(req.query.app); // $ Alert[js/path-injection]
  kiosk.open(req.query.file);
  res.end();
});

app.get("/report", async (req, res) => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.pdf({ path: req.query.file }); // $ Alert[js/path-injection]
  kiosk.pdf({ path: req.query.file });
  res.end();
});

app.get("/inside", (req, res) => {
  // `node:path` e `path.resolve` com a checagem de prefixo.
  const root = "/srv/files";
  const absolute = path.resolve(root, req.query.file);
  if (absolute.startsWith(root)) {
    res.send(fs.readFileSync(absolute));
  }
});
