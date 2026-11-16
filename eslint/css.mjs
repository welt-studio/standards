// Todo CSS numa camada de cascata (decisão do PO, 2026-11-16): a ordem das camadas
// (`@layer theme, base, components, utilities`) decide a cascata, não o conteúdo de cada pacote.
// CSS de pacote fora de camada vence as utilities do Tailwind sem aviso (o `material-symbols` no
// ComicHub travou todo ícone em 24px). A regra oficial do `@eslint/css`, com os padrões dela,
// reprova `@import` sem `layer()`, regra fora de `@layer` e camada sem nome; diretiva do Tailwind
// (`@theme`, `@utility`, `@custom-variant`, `@source`) não é regra e fica no topo. O
// `tailwind-csstree` é a sintaxe do Tailwind 4 para o parser do `@eslint/css`; sem ela, o
// `@custom-variant` dá erro de parse.
import css from "@eslint/css";
import { tailwind4 } from "tailwind-csstree";

export const cssConfigs = [
  {
    name: "welt/css",
    files: ["**/*.css"],
    plugins: { css },
    language: "css/css",
    languageOptions: { customSyntax: tailwind4 },
    rules: { "css/use-layers": "error" },
  },
];
