# Parking Lot

Coisas que surgem no meio do caminho e não podem se perder: dúvidas, decisões adiadas, tarefas soltas, ideias. Caixa de captura, não kanban — prioriza-se na triagem. Feature nova vai para `ROADMAP.md`; problema em código vai para `TECH_DEBT.md`.

## Decisões pendentes

### [Segurança] Paridade com o CodeQL: portar as regras para o Semgrep e travar a CI

- [ ] `2026-11-13`
- **Contexto**: o assessment gratuito do GitHub achou vulnerabilidades em 15 dos 25 repos. O Code
  Security, que roda o CodeQL, custa US$30 por mês e não fica, por decisão do PO. As 143 consultas da
  suíte padrão do CodeQL (Python 41, JS/TS 85, Actions 17) foram portadas para regras do Semgrep Pro.
  As regras, o medidor e a tabela de paridade estão no `wip/codeql-port.tar.gz` da branch
  `feat/security`.
- **Item**: o primeiro porte ficou raso. Ele acertou 73% dos testes do próprio CodeQL e 62 dos 79
  alertas reais em 4 repos. Python e Actions ficaram perto do CodeQL; o JS/TS, longe.
  - **Diagnóstico de 2026-11-13.** Foram sorteadas 100 perdas, 20 de cada uma das 5 consultas grandes
    do JS: `xss`, `path-injection`, `sql-injection`, `code-injection` e `command-line-injection`.
    - **40 eram regra rasa.** Algumas estavam presas a nomes do teste, como `promisifiedExec`.
    - **53 eram modelo de API que faltava.** Exemplos: mkdirp, rimraf, execa, MongoDB `$where`,
      MooTools, Relay, S3 Select, DynamoDB PartiQL.
    - **7 são limite do Semgrep**, cada um com uma reprodução mínima:
      - `.vue`, que não é lido;
      - taint no `<script>` dentro de `.html`;
      - callback registrado antes do dado;
      - `wrap(f)(x)`;
      - campo de objeto no encontro de um `if`.
    - Com as regras novas, `sql-injection` foi de 70% para 90% e `code-injection` de 66% para 100%.
      Em troca, cresceram os achados a mais.
  - **Gabarito**: o CodeQL foi ligado em 19 repos e deu 137 alertas. Ele vale só até o fim do
    trial, por volta de 2026-12-11. Depois disso, não há mais com o que comparar.
  - **Linha de base nos 19 repos (primeiro porte)**: pegou 120 dos 137 alertas e deu 303 achados a
    mais.
    - Perfeitos: Actions (`missing-workflow-permissions` 42/42, cache poisoning 8/8).
    - Um repo que ninguém usou durante o porte ficou em 38/40, sinal de que as regras não
      decoraram os repos de ajuste.
    - O barulho se concentra em poucas regras: `js/html-constructed-from-input` 88,
      `py/path-injection` 42, `js/unvalidated-dynamic-method-call` 33,
      `py/http-response-splitting` 28, `js/xss-through-dom` 26.
  - **Critério de paridade proposto, ainda não aprovado**:
    - os alertas reais todos pegos, menos os falsos positivos do próprio CodeQL;
    - pelo menos 90% dos testes do CodeQL em toda regra que bloqueia a CI;
    - cada achado a mais revisado;
    - os 7 limites registrados como lacuna conhecida.
  - **Como conferir o porte**:
    - testes do CodeQL com as marcações de alerta e de não-alerta;
    - metade dos testes para ajustar e a outra metade para medir, mais um script que reprova regra
      com nome do teste;
    - comparar a lista de APIs dos modelos do CodeQL com a da regra;
    - os alertas reais;
    - `semgrep --test` com exemplos no standards;
    - revisão independente.
  - **Custo de manter**: o plano gratuito do Semgrep cobre até 10 repos privados e a org tem 25.
    Falta confirmar se a varredura local (`scan --pro`) entra nessa conta.
  - **Testes das regras, em duas camadas**: hoje as regras portadas não têm teste próprio. O
    `parity.py` foi uma medição avulsa, na pasta temporária, que não roda no CI nem reprova nada.
    Nenhuma regra entra no standards sem as duas camadas, e o `semgrep --test` roda as duas no CI.
    1. **Os testes do próprio CodeQL**, que são MIT, viram arquivos de exemplo ao lado de cada
       regra, com `ruleid:` nas linhas do `.expected` e `ok:` nas outras. São a base: medem se o
       porte faz o que o CodeQL faz, em todos os frameworks.
    2. **Exemplos extras na nossa stack** (Django/DRF, FastAPI, React, TanStack, Actions), numa pasta
       do standards. Conferem os frameworks que usamos, onde os testes do CodeQL são fracos.
       - O gabarito deles também vem do CodeQL: o standards é público, então a análise do GitHub
         roda nele de graça e continua depois do trial.
       - Um teste compara o que o CodeQL acusa com o que a regra acusa.
       - Decidir se os alertas dessa pasta ficam separados na aba de segurança ou documentados
         como esperados.
       - Para rodar a CLI do CodeQL localmente ou no CI, o standards precisa de uma licença de
         código aberto (MIT ou Apache-2.0). Hoje ele não tem. É decisão do PO.
  - **O motor**: medir quanto da paridade sobra no Semgrep CE (sem o `--pro`, sem conta e sem
    limite de repos), para saber se o Pro é indispensável.
  - **Ordem decidida pelo PO (2026-11-13): os testes entram primeiro.**
    - Os testes do CodeQL entram no standards já com todas as regras.
    - O caso que a regra já pega fica como `ruleid:` e passa a ser travado.
    - O que ela ainda perde fica como `todoruleid:`, de modo que o CI continua verde e cada
      pendência fica registrada no repositório, não numa pasta temporária.
    - O teste diz o que falha, não por quê. Cada `todoruleid:` passa pelo diagnóstico (regra rasa,
      modelo faltando ou limite do motor, este com reprodução mínima). Quem diagnostica e corrige é
      o Claude, e a regra corrigida troca `todoruleid:` por `ruleid:`.
    - Antes de depender disso, conferir se o `semgrep --test` reprova quando um `todoruleid:` passa
      a ser pego. Se não reprovar, um teste próprio faz essa conferência, para nenhuma pendência
      ficar marcada depois de resolvida.
- **Próximo passo**: o PO aprova o critério. Depois, refazer o porte consulta por consulta,
  ajustando em um repo só e validando nos 19 no fim de cada etapa, de
  preferência antes de o trial acabar.

### [Rust] Padrão de lint para Rust

- [ ] `2026-11-13`
- **Contexto**: no censo da segurança apareceu que o standards só cobre Rust no jscpd e no
  `rustsec/audit-check`. nebul-ai, hyleumworks-studio, ylem e shapeshifter-studio têm Rust. O
  shapeshifter roda `cargo fmt --check` e `cargo clippy -- -D warnings` por hooks locais.
- **Item**: um padrão do standards para Rust, como o do Ruff e do ESLint: clippy com os lints de
  segurança e de qualidade, rustfmt e talvez `cargo-deny`, publicado como hook.
- **Próximo passo**: levantar o que os 4 repos usam hoje (`Cargo.toml` `[lints]`, `clippy.toml`,
  `rust-toolchain.toml`) e propor a base.

## Tarefas soltas

### [Release] Atualizar a `feat/security` a partir da `main`, com o ESLint indo para a 4.8.0

- [ ] `2026-11-13`
- **Contexto**: a `feat/security` (zizmor, no-unsanitized, `Math.random`, gitleaks no histórico,
  `gitignore-base`) subiu o `eslint/package.json` para 4.7.0. Enquanto isso, a `main` publicou a
  `eslint-v4.7.0` e a `eslint-v4.7.1` (regra de CSS do front).
- **Item**: atualizar a branch a partir da `main` e resolver o conflito no `eslint/package.json` e
  no README: a versão vai para 4.8.0 e ficam as duas seções do README.
  - O rebase precisa de árvore limpa, e o `docs/TECH_DEBT.md` tem alteração pendente do PO.
  - Antes de publicar, decidir o destino do `wip/codeql-port.tar.gz`, que não deve ir para a
    `main`.
  - Ao publicar, criar as tags `eslint-v4.8.0`, `security-v1.0.0` e `gitignore-v1.0.0`.
- **Próximo passo**: com o `TECH_DEBT.md` resolvido, `git rebase main` na `feat/security`.
