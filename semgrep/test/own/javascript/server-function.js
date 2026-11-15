// own-test: js/code-injection, js/command-line-injection
"use server";
// Com a diretiva no arquivo, todo parâmetro de função exportada é do usuário (React.qll).
import { exec } from "child_process";

export async function runScript(label, script, extra) {
  eval(script); // $ Alert[js/code-injection]
  exec(label); // $ Alert[js/command-line-injection]
  eval(extra); // $ Alert[js/code-injection]
}

export const arrow = async (first, second) => {
  eval(second); // $ Alert[js/code-injection]
};

// Função que o arquivo não exporta não recebe dado do cliente.
function internal(text) {
  eval(text);
}
