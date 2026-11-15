// own-test: js/code-injection, js/command-line-injection
// Fontes e sumidouros escritos com `import` nomeado (GraphQL, WebView, child_process, execa).
import { GraphQLObjectType, GraphQLString } from "graphql";
import { WebView } from "react-native";
import { exec as run, spawn } from "node:child_process";
import { execa, $ } from "execa";
import express from "express";

const app = express();

// O 2o parâmetro do `resolve` de um `GraphQLObjectType` importado por nome é do usuário.
export const Mutation = new GraphQLObjectType({
  name: "Mutation",
  fields: {
    runEval: {
      type: GraphQLString,
      resolve: (_parent, { value }) => {
        eval(value); // $ Alert[js/code-injection]
        run(value); // $ Alert[js/command-line-injection]
        return "ok";
      },
    },
  },
});

// Um objeto qualquer com `resolve` não é fonte.
export const plain = {
  resolve: (_parent, { value }) => {
    eval(value);
    run(value);
  },
};

app.get("/view", (req, res) => {
  const tainted = req.query.script;
  const webView = <WebView />;
  webView.injectJavaScript(tainted); // $ Alert[js/code-injection]
  const other = { injectJavaScript: (text) => text };
  other.injectJavaScript(tainted);
  res.end();
});

app.get("/commands", async (req, res) => {
  const cmd = req.query.cmd;
  run(cmd); // $ Alert[js/command-line-injection]
  spawn(cmd); // $ Alert[js/command-line-injection]
  await execa(cmd, ["--help"]); // $ Alert[js/command-line-injection]
  await $`${cmd} --help`; // $ Alert[js/command-line-injection]
  res.end();
});
