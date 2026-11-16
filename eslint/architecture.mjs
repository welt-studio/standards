// Arquitetura do app (decisão do PO, 2026-10-27): as regras de direção do bulletproof-react com as
// rotas por arquivo do TanStack Router. Toda pasta de `src/` é uma camada, e cada camada só importa as
// de baixo:
//   os arquivos de entrada na raiz de `src/` (`main.tsx`, `entry-server.tsx` do prerender SSR,
//   `routeTree.gen.ts`, `vite-env.d.ts`) e `app/` → tudo;
//   `routes/` (rota fina: parâmetros, busca, loader, guarda) → features e base;
//   `features/<nome>/` → a própria feature e a base, nunca outra feature;
//   base (`components`, `hooks`, `lib`, `stores`, `types`, `utils`, `config`, `assets`, `testing`) → base.
// Quem junta duas features é a rota ou o `app/`; o que duas features usam sobe para a base. Pasta ou
// arquivo de `src/` fora dessa lista reprova (`no-unknown-files`): `App.tsx` e `router.tsx` moram em
// `app/`. Os padrões casam pela direita, então valem igual na raiz do projeto e num app de monorepo
// (`apps/admin/src/...`).
import { createRequire } from "node:module";

import boundaries from "eslint-plugin-boundaries";

import { toolConfigFiles } from "./files.mjs";

const SHARED_FOLDERS = "(components|hooks|lib|stores|types|utils|config|assets|testing)";
const architectureSettings = {
  "boundaries/files": [
    {
      pattern: "**/src/{main.tsx,entry-server.tsx,routeTree.gen.ts,vite-env.d.ts}",
      category: "entry",
    },
  ],
  "boundaries/elements": [
    { type: "app", pattern: "src/app" },
    { type: "route", pattern: "src/routes" },
    { type: "feature", pattern: "src/features/*", capture: ["featureName"] },
    { type: "shared", pattern: `src/${SHARED_FOLDERS}` },
  ],
};
const everyLayer = [
  { to: { element: { type: ["app", "route", "feature", "shared"] } } },
  { to: { file: { categories: "entry" } } },
];
const architectureRules = {
  "boundaries/no-unknown-files": "error",
  "boundaries/dependencies": [
    "error",
    {
      default: "disallow",
      policies: [
        { from: { file: { categories: "entry" } }, allow: everyLayer },
        { from: { element: { type: "app" } }, allow: everyLayer },
        {
          from: { element: { type: "route" } },
          allow: [{ to: { element: { type: ["route", "feature", "shared"] } } }],
        },
        {
          from: { element: { type: "feature" } },
          allow: [
            {
              to: {
                element: { type: "feature", captured: { featureName: "{{ from.featureName }}" } },
              },
            },
            { to: { element: { type: "shared" } } },
          ],
        },
        { from: { element: { type: "shared" } }, allow: [{ to: { element: { type: "shared" } } }] },
      ],
    },
  ],
};

// Rota fina: a tela mora na feature, e o arquivo de rota só tem `createFileRoute` com parâmetros,
// busca, loader e guarda. O limite trava a tela de voltar para a rota (decisão do PO, 2026-10-27).
const ROUTE_MAX_LINES = 60;

// CSS só pelo `src/index.css` (decisão do PO, 2026-11-16, que revoga a de 2026-11-12). O CSS tem uma
// porta: o `main.tsx` importa só o `./index.css`, e o nosso CSS e o de pacote entram nele por
// `@import`. A cascata e o `@layer` moram nessa porta: só pelo `@import` do CSS o pacote que define
// classe entra numa camada (`layer(base)`) e não vence as utilities do Tailwind. O Knip lê esse
// `@import` pelo plugin do Tailwind, ligado no workspace que declara `tailwindcss` (ou
// `@tailwindcss/vite`); sem ele, acusa o pacote como sem uso. O ESLint não lê o CSS, mas lê o `import`
// de CSS do TS, e é por ele que a regra é travada.
// O `.css` com ou sem o sufixo de query do Vite (`?inline`, `?url`, `?raw`): o sufixo muda o que o
// import devolve, não o fato de ser CSS.
const CSS_IMPORT = "\\.css(\\?.*)?$";
const CSS_OUTSIDE_MAIN_MESSAGE =
  'CSS não se importa no TS: o nosso e o de pacote entram por `@import` no `src/index.css` (ex.: `@import "pacote/x.css" layer(base);`).';
const CSS_IN_MAIN_MESSAGE =
  'O `main.tsx` importa só o `./index.css`: o CSS de pacote vai para ele por `@import` (ex.: `@import "pacote/x.css" layer(base);`, sem `layer()` se só tem `@font-face`).';
// `import()` de CSS: o `no-restricted-imports` só vê o import estático.
const dynamicCssImport = {
  selector: `ImportExpression[source.value=/${CSS_IMPORT}/]`,
  message: CSS_OUTSIDE_MAIN_MESSAGE,
};
const cssOutsideMainRules = {
  "no-restricted-imports": [
    "error",
    { patterns: [{ regex: CSS_IMPORT, message: CSS_OUTSIDE_MAIN_MESSAGE }] },
  ],
  "no-restricted-syntax": ["error", dynamicCssImport],
};
const cssInMainRules = {
  "no-restricted-imports": [
    "error",
    // Qualquer CSS que não seja o `./index.css`, inclusive o de pacote.
    {
      patterns: [{ regex: `^(?!\\./index\\.css$).*${CSS_IMPORT}`, message: CSS_IN_MAIN_MESSAGE }],
    },
  ],
  "no-restricted-syntax": ["error", dynamicCssImport],
};

// O boundaries resolve os imports pelo `import/resolver` legado (do `eslint-module-utils`), não pelo
// `resolver-next` do import-x: sem o resolver do TypeScript, import por alias (`@/features/...`) não
// resolve e passa sem ser conferido. O resolver vai pelo caminho absoluto, uma das formas documentadas
// do `import/resolver` (o README do `eslint-plugin-import`: "filesystem path to resolver"): ele é
// dependência deste pacote, e o projeto não o declara. Pelo nome, ele só seria achado pelo hoist
// interno do pnpm (`node_modules/.pnpm/node_modules`), que não é contrato.
const TYPESCRIPT_RESOLVER = createRequire(import.meta.url).resolve(
  "eslint-import-resolver-typescript",
);

// App Vite: a estrutura de pastas e a direção dos imports do padrão, em `src/`. Só no app: pacote e
// biblioteca não têm rota nem feature.
export function architectureConfigs(framework, files, resolverOptions) {
  if (framework !== "vite") {
    return [];
  }
  const inSrc = (folder) => files.map((pattern) => [pattern, `**/src/${folder}**`]);
  return [
    {
      name: "welt/architecture",
      files: inSrc(""),
      ignores: toolConfigFiles,
      plugins: { boundaries },
      settings: {
        ...architectureSettings,
        "import/resolver": { [TYPESCRIPT_RESOLVER]: resolverOptions },
      },
      rules: architectureRules,
    },
    {
      name: "welt/thin-routes",
      files: inSrc("routes/"),
      rules: {
        "max-lines": ["error", { max: ROUTE_MAX_LINES, skipBlankLines: true, skipComments: true }],
      },
    },
    {
      name: "welt/css-outside-main",
      files: inSrc(""),
      ignores: ["**/src/main.tsx"],
      rules: cssOutsideMainRules,
    },
    { name: "welt/css-in-main", files: inSrc("main.tsx"), rules: cssInMainRules },
  ];
}
