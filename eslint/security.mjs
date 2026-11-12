// Segurança no código do front, as falhas que o CodeQL acusou nos projetos e que têm trava mecânica
// no lint. O `dangerouslySetInnerHTML` e a URL `javascript:` do React ficam com o `@eslint-react`
// (`dom-no-dangerously-set-innerhtml`, `dom-no-script-url`).
import noUnsanitized from "eslint-plugin-no-unsanitized";

// O `Math.random()` é previsível: senha, token ou id gerado com ele pode ser adivinhado (o
// `js/insecure-randomness` do CodeQL; no Python, o `S311` do Ruff). Um id que não protege nada
// também usa o `crypto`: uma regra só, sem exceção para decidir caso a caso.
const weakRandomRules = {
  "no-restricted-properties": [
    "error",
    {
      object: "Math",
      property: "random",
      message:
        "Use `crypto.getRandomValues()` ou `crypto.randomUUID()`: o `Math.random()` é previsível.",
    },
  ],
};

/**
 * As regras de segurança, em todo arquivo lintado (com e sem tipo).
 * @param {string[]} files
 */
export function securityConfigs(files) {
  return [
    // HTML montado a partir de texto que chega ao DOM sem sanitizar (`innerHTML`, `outerHTML`,
    // `insertAdjacentHTML`, `document.write`): XSS.
    { name: "welt/no-unsanitized", ...noUnsanitized.configs.recommended, files },
    { name: "welt/weak-random", files, rules: weakRandomRules },
  ];
}
