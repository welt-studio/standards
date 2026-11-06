// Teste do pacote: o `weltConfig` aplicado ao monorepo mínimo de `fixture/` reprova exatamente o que
// a arquitetura do front e os imports do padrão proíbem, e nada além. Cada arquivo do fixture é um
// caso; o comentário no topo dele diz o que ele testa. Roda com `pnpm test` nesta pasta.
//
// O fixture roda como num projeto que instala o pacote:
// - o pacote montado só com o que o `files` do `package.json` publica: arquivo esquecido na lista
//   quebra aqui, não nos projetos depois da tag;
// - copiado para uma pasta fora deste pacote: daqui de dentro, o resolver do TypeScript seria achado
//   pelo nome no `node_modules` do pacote, o que num projeto com pnpm não acontece;
// - num repositório git próprio: o resolver dos aliases lista os `tsconfig.json` versionados, e o que
//   o `.gitignore` do fixture ignora fica fora do lint;
// - com o processo na pasta dele, como o `eslint` da linha de comando roda na raiz do projeto: o
//   `eslint-import-resolver-typescript` 4.4.5 deixa de usar os `tsconfig` (e com eles os aliases)
//   quando o `cwd` do ESLint difere do diretório do processo.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import {
  cpSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, before, test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

import { ESLint } from "eslint";

const FIXTURE = fileURLToPath(new URL("fixture", import.meta.url));
const PACKAGE = fileURLToPath(new URL("..", import.meta.url));

/**
 * Monta em `target` o pacote como o projeto o recebe: o `package.json` e o que o `files` lista. As
 * dependências vêm do `node_modules` deste pacote, por link.
 */
function installPackage(target) {
  const manifest = JSON.parse(readFileSync(join(PACKAGE, "package.json"), "utf8"));
  mkdirSync(target, { recursive: true });
  for (const file of ["package.json", ...manifest.files]) {
    cpSync(join(PACKAGE, file), join(target, file), { recursive: true });
  }
  symlinkSync(join(PACKAGE, "node_modules"), join(target, "node_modules"), "dir");
  return pathToFileURL(join(target, manifest.exports["."].default)).href;
}

// As regras que este teste cobre. As outras do padrão também rodam no fixture, mas não são o
// assunto aqui.
const COVERED_RULES = new Set([
  "boundaries/dependencies",
  "boundaries/no-unknown-files",
  "import-x/no-cycle",
  "max-lines",
  "@typescript-eslint/only-throw-error",
]);

// O que cada arquivo do fixture deve reprovar; arquivo fora daqui não reprova nenhuma das regras.
const EXPECTED = {
  "apps/web/src/App.tsx": ["boundaries/no-unknown-files"],
  "apps/web/src/helpers/value.ts": ["boundaries/no-unknown-files"],
  "apps/web/src/features/goals/components/goals-page.ts": ["boundaries/dependencies"],
  "apps/web/src/lib/reaches-feature.ts": ["boundaries/dependencies"],
  "apps/web/src/lib/cycle-a.ts": ["import-x/no-cycle"],
  "apps/web/src/lib/cycle-b.ts": ["import-x/no-cycle"],
  "apps/web/src/routes/fat.ts": ["max-lines"],
  "apps/web/src/lib/throw-response.ts": ["@typescript-eslint/only-throw-error"],
};

// Arquivo que o `.gitignore` do fixture ignora, criado depois do `git add` (versionado aqui, ele
// seria ignorado também pelo git deste repo). Fora da estrutura de `src/` e com `[id]` no nome: se o
// `gitIgnored` falhar, ou deixar o nome virar glob, ele aparece reprovando o `no-unknown-files`.
const GIT_IGNORED_FILE = join("apps", "web", "src", "local-[id]", "page.ts");

let project;
// O teste muda a pasta do processo e a variável de ambiente: o `after` devolve as duas como estavam,
// para nenhum outro teste do mesmo processo herdar o fixture.
const originalCwd = process.cwd();
const originalConfig = process.env.WELT_ESLINT_CONFIG;

before(() => {
  project = join(mkdtempSync(join(tmpdir(), "welt-eslint-")), "project");
  cpSync(FIXTURE, project, { recursive: true });
  execFileSync("git", ["init", "--quiet"], { cwd: project });
  execFileSync("git", ["add", "--all"], { cwd: project });
  mkdirSync(join(project, GIT_IGNORED_FILE, ".."));
  writeFileSync(join(project, GIT_IGNORED_FILE), "export const page = 1;\n");
  process.env.WELT_ESLINT_CONFIG = installPackage(
    join(project, "..", "node_modules", "@welt-studio", "eslint-config"),
  );
  // O `@tanstack/router-core` do caso do `throw redirect(...)`, como num projeto com o TanStack
  // Router: a exceção do `only-throw-error` casa pelo pacote que declara o tipo, então precisa ser o
  // pacote de verdade, não um stub.
  mkdirSync(join(project, "..", "node_modules", "@tanstack"), { recursive: true });
  symlinkSync(
    join(PACKAGE, "node_modules", "@tanstack", "router-core"),
    join(project, "..", "node_modules", "@tanstack", "router-core"),
    "dir",
  );
  process.chdir(project);
});

after(() => {
  process.chdir(originalCwd);
  if (originalConfig === undefined) {
    delete process.env.WELT_ESLINT_CONFIG;
  } else {
    process.env.WELT_ESLINT_CONFIG = originalConfig;
  }
  rmSync(join(project, ".."), { recursive: true, force: true });
});

test("o fixture reprova só o que a arquitetura e os imports proíbem", async () => {
  const results = await new ESLint().lintFiles(["apps", "packages"]);

  const fatal = results.flatMap((result) =>
    result.messages.filter((message) => message.fatal).map((message) => message.message),
  );
  assert.deepEqual(fatal, [], "nenhum arquivo do fixture pode falhar no parse");

  const found = Object.fromEntries(
    results
      .map((result) => [
        result.filePath.slice(project.length + 1),
        [
          ...new Set(
            result.messages
              .map((message) => message.ruleId)
              .filter((ruleId) => COVERED_RULES.has(ruleId)),
          ),
        ].sort(),
      ])
      .filter(([, rules]) => rules.length > 0),
  );
  assert.deepEqual(found, EXPECTED);
});

test("o que o git ignora fica fora do lint", async () => {
  // O caso só vale se o git de fato ignora o arquivo (o `check-ignore` sai com erro se não ignora).
  execFileSync("git", ["check-ignore", "--quiet", GIT_IGNORED_FILE], { cwd: project });
  const linted = (await new ESLint().lintFiles(["apps"])).map((result) =>
    result.filePath.slice(project.length + 1),
  );
  assert.ok(linted.includes(join("apps", "web", "src", "App.tsx")), "o fixture foi lintado");
  assert.ok(!linted.includes(GIT_IGNORED_FILE), `${GIT_IGNORED_FILE} foi lintado`);
});
