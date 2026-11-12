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

// CSS só pelo `main.tsx` (decisão do PO, 2026-11-12). O nosso entra pelo `./index.css`, a porta do
// CSS global, que puxa os outros por `@import`. O de pacote (as fontes do `@fontsource`) entra por
// `import` no `main.tsx`, antes do `./index.css`, como a documentação do Fontsource e do Vite mostra:
// por `@import` no CSS, o Knip não vê a dependência, porque só lê CSS pelo plugin do Tailwind. O ESLint
// não lê o CSS, mas lê o `import` de CSS do TS, e é por ele que a regra é travada.
const CSS_IMPORT = "\\.css$";
const cssOutsideMainRules = {
  "no-restricted-imports": [
    "error",
    {
      patterns: [
        {
          regex: CSS_IMPORT,
          message:
            "CSS entra só pelo `main.tsx`: o nosso por `@import` no `src/index.css`, o de pacote por `import` no `main.tsx`.",
        },
      ],
    },
  ],
};
const cssInMainRules = {
  "no-restricted-imports": [
    "error",
    {
      patterns: [
        {
          // Relativo ou por alias, e não o `./index.css`: o nosso CSS entra por `@import` nele.
          regex: "^(?!\\./index\\.css$)(\\.|@/).*\\.css$",
          message:
            "O nosso CSS entra por `@import` no `src/index.css`; o `main.tsx` só importa o `./index.css` e o CSS de pacote.",
        },
      ],
    },
  ],
  // O `./index.css` por último: o CSS de pacote vem antes, e o nosso, carregado depois, prevalece na
  // cascata. Depois dele, nenhum import só de efeito (CSS de pacote também entra assim).
  "no-restricted-syntax": [
    "error",
    {
      selector:
        "ImportDeclaration[source.value='./index.css'] ~ ImportDeclaration[specifiers.length=0]",
      message:
        "O `./index.css` é o último import de CSS do `main.tsx`: o CSS de pacote vem antes dele.",
    },
  ],
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
