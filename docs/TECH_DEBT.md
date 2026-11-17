# Débitos Técnicos

## Segurança

### [ESLint] `minimatch` 10 vulnerável no pacote do ESLint (GHSA-g3hv-75wg-m249)

- [ ] **Severidade**: Média · `2026-11-16`
- **Arquivos**: `package.json`, `eslint/package.json`, `pnpm-workspace.yaml`, `pnpm-lock.yaml`
- **Descrição**: o `minimatch` < 11.0.1 tem negação de serviço por glob (alerta moderado no
  `main`). O risco é baixo: o atacante precisa controlar o padrão de glob, e no lint quem escreve os
  padrões somos nós. Cinco pacotes puxam o 10.2.6:
  - `eslint` 10.12.0: corrigido na 10.15.0 (2026-11-13);
  - `@eslint/config-array` 0.23.5: corrigido na 0.23.6 (2026-11-13);
  - `@typescript-eslint/typescript-estree` 8.72.0: corrigido na 8.73.0 (2026-11-16);
  - `eslint-plugin-import-x` 4.17.1: corrigido na 4.18.1 (2026-11-09);
  - `eslint-plugin-jsx-a11y-x` 0.2.0: sem correção (a última versão é de maio e ainda pede
    `^10.2.5`).

  Decisão do PO (`2026-11-16`): esperar as versões completarem os 7 dias da política, sem exceção de
  idade.

- **Sugestão**: a partir de `2026-11-23`, quando o `typescript-eslint` 8.73.0 completa 7 dias:
  1. subir `eslint`, `typescript-eslint` e `eslint-plugin-import-x`;
  2. no `eslint-plugin-jsx-a11y-x`, `overrides` do pnpm com faixa fechada
     (`eslint-plugin-jsx-a11y-x>minimatch: 11.0.5`), com o teste do pacote verde;
  3. publicar a `eslint-v6.0.1` e conferir no GitHub que o alerta fechou.

### [Renovate] Alertas do Dependabot e Renovate: repensar quem avisa e quem corrige

- [ ] **Severidade**: Baixa · `2026-11-16`
- **Arquivos**: `renovate/default.json5` (`vulnerabilityAlerts`, `osvVulnerabilityAlerts`),
  configuração de segurança dos repos no GitHub
- **Descrição**: hoje são duas peças.
  - **Alertas do Dependabot**, ligados nos repos: detectam a falha (inclusive em dependência
    indireta) e o GitHub avisa no `git push`.
  - **Renovate**: abre os PRs. As atualizações do Dependabot estão desligadas: sem
    `dependabot.yml`, e `automated-security-fixes` desligado.

  O Renovate lê os alertas do GitHub pelo `vulnerabilityAlerts`, mas não abriu PR para o `minimatch`
  (débito acima): a correção é major numa dependência indireta, fora da faixa dos pacotes que a
  pedem. O OSV do Renovate confere só dependência direta. A falha ficou visível só pelo aviso do
  GitHub, e o PO quer repensar a divisão entre os dois (`2026-11-16`).

- **Sugestão**: levantar com o PO:
  - se os alertas do Dependabot ficam como a fonte de detecção;
  - como uma falha indireta sem PR do Renovate vira trabalho: por exemplo, a auditoria semanal
    (`pnpm audit`) também no standards, ou uma regra do Renovate para `overrides`;
  - se alguma peça sobra.

## Produção / Infra

### [Renovate] `rustsec/audit-check` fora do Renovate, preso num commit do `main`

- [ ] **Severidade**: Média · `2026-10-28`
- **Arquivos**: `renovate/default.json5`
- **Descrição**: a última release do `rustsec/audit-check` é a v2.0.0 (2024), que roda em Node 20,
  e o GitHub está tirando o Node 20 dos runners. A migração para Node 24 (rustsec/audit-check#48)
  entrou no `main` em 2026-03-20, mas ainda não saiu em tag (conferido em 2026-10-28). Os projetos
  usam a action fixada no commit do `main`, e a regra `enabled: false` do preset impede o Renovate
  de propô-la: correção de segurança da própria action, ou release nova, não chega a ninguém
  sozinha.
- **Sugestão**: quando sair release com Node 24, tirar a regra do preset; o Renovate passa a
  fixar a action pelo SHA da tag, como as outras (`helpers:pinGitHubActionDigests`). Até lá,
  conferir a cada rodada mensal se a release saiu.

## Arquitetura / Design

### [Python] Migração dos projetos para o `python-base` aplicada, sem commit

- [ ] **Severidade**: Média · `2026-11-07`
- **Arquivos**: nos 6 projetos, `.pre-commit-config.yaml`, `.python-version`, Dockerfiles,
  `pyproject.toml`, `uv.lock`, workflows e docs
- **Descrição**: a versão do Python mora só no `python/.python-version` deste repo (decisão do PO,
  `2026-11-07`), com o hook `python-base` (`python-v1.0.0`), e o preset já não propõe Python fora
  daqui. A migração foi aplicada no working tree de comichub, flowbit, nebulai, pg-studio,
  shapeshifter-studio e welt-studio (`2026-11-08`), por cima de trabalho não commitado, e ainda não
  foi commitada: até lá, a CI dos projetos roda o padrão antigo. Em comichub, pg-studio,
  shapeshifter-studio e welt-studio o `.python-version` do pacote não é versionado, e os Dockerfiles
  novos dependem dele.
- **Sugestão**:
  1. em cada projeto, commitar a migração **com** o `.python-version` do pacote (sem ele, o build do
     deploy quebra e o `python-base` reprova na CI). O commit que muda `pyproject.toml`/`uv.lock` roda
     o `ruff --fix` e o Pyright no pacote inteiro: separar o que for fila antiga;
  2. corrigir os docs que ainda dizem que o projeto declara o Python ou não listam o `python-base`
     (flowbit, nebulai e pg-studio: `CLAUDE.md`/`AGENTS.md`/`docs/INFRASTRUCTURE.md`);
  3. pg-studio: a imagem da API instala pelo `requirements.txt`, fora do `uv.lock` (débito do
     projeto);
  4. subir o `rev` do `python-base` para `python-v1.1.0` e o do `pnpm-base` para `pnpm-v1.1.0`
     (as tags das imagens do uv e do pnpm passam a ter trava). No comichub, tirar o passo
     "Dockerfiles agree with packageManager" do `frontend.yml`, que o `pnpm-base` substitui;
  5. ao fim, tirar o gerenciador regex do `uvx` do preset, se nenhum projeto o usar mais.

### [ESLint] Projetos ainda no CSS da v4 (migração para a `eslint-v6.1.0`)

- [ ] **Severidade**: Média · `2026-11-16`
- **Arquivos**: nos projetos, `src/main.tsx` e `src/index.css` dos frontends
- **Descrição**: na v5 (decisão do PO, `2026-11-16`), todo CSS de pacote entra por `@import` no
  `src/index.css`, e o `main.tsx` importa só o `./index.css`. O que a v4 aceitava reprova. A
  v6.0.0 lintava o CSS e não serve. A v6.1.0 tira esse lint e tem as mesmas regras da v5; é para
  ela que se sobe.

  Os 6 projetos que usam o pacote, com a tag de hoje:

  | Projeto                           | Tag             |
  | --------------------------------- | --------------- |
  | comichub                          | `eslint-v4.7.1` |
  | welt-studio (pelo `catalog`)      | `eslint-v4.7.1` |
  | flowbit (`frontend/`)             | `eslint-v4.7.1` |
  | pg-studio                         | `eslint-v4.6.0` |
  | nebulai                           | `eslint-v4.6.0` |
  | shapeshifter-studio (`frontend/`) | `eslint-v4.6.0` |

  O que já se sabe de cada um:
  - **welt-studio**: os apps importam o `@fontsource` no `main.tsx`. O Tailwind está declarado no
    `packages/ui` e no `packages/vite-config`, não nos apps, então o Knip dos apps não lê o
    `@import` do CSS.
  - **ComicHub**: tem no working tree, sem commit, a migração para a v6.0.0, que é o débito do item 2
    da Adequação.

- **Sugestão**: em cada frontend, ao subir para a v6.1.0:
  1. o CSS de pacote sai do `main.tsx` e entra por `@import` no `index.css`;
  2. o que define classe entra com `layer(base)`.

  O nosso CSS não muda.

  Por projeto:
  - **welt-studio**: os `@import` das fontes vão para o CSS do `packages/ui`, onde o Tailwind é
    declarado.
  - **ComicHub**: o `@import "material-symbols/outlined.css" layer(base)` fica, e o resto da
    migração para a v6.0.0 volta atrás: a forma expandida do Tailwind, o nosso CSS em
    `@layer base` e o `css` no `types_or`. As instruções foram mandadas à sessão do projeto.
  - **flowbit, pg-studio, nebulai e shapeshifter-studio**: conferir se há CSS de pacote no
    `main.tsx`.

### [jscpd] Projetos ainda com o relatório semântico (migração para a `jscpd-v2.0.0`)

- [ ] **Severidade**: Baixa · `2026-11-17`
- **Arquivos**: nos projetos, `.pre-commit-config.yaml` (`rev` do `jscpd-base`), `.jscpd-semantic.json`
  e o `package.json` que tem o script `duplication:semantic`
- **Descrição**: decisão do PO (`2026-11-17`): sai o relatório semântico do jscpd, que rodava um
  modelo de embeddings sobre o código. A `jscpd-v2.0.0` deixa de gerar o `.jscpd-semantic.json`, mas
  não apaga a cópia que já está no projeto (o PO decidiu sem código de limpeza no hook, que só
  serviria uma vez): sem a limpeza, a cópia fica órfã, e o script `duplication:semantic`, que também
  sai só a mão, continua lendo uma config que o hook não atualiza mais. A cópia só fica inofensiva
  depois que o script sai; nada trava a limpeza além deste item. Os 6 projetos estão na
  `jscpd-v1.0.3`:

  | Projeto             | Onde está o script      |
  | ------------------- | ----------------------- |
  | comichub            | `package.json`          |
  | welt-studio         | `package.json`          |
  | flowbit             | `frontend/package.json` |
  | pg-studio           | `package.json`          |
  | nebulai             | `package.json`          |
  | shapeshifter-studio | `frontend/package.json` |

  O shapeshifter-studio também tem o `backend/tests/test_jscpd_config.py`, que compara as duas
  configs.

- **Sugestão**: em cada projeto, ao subir o `rev` do `jscpd-base` para a `jscpd-v2.0.0`:
  1. apagar o `.jscpd-semantic.json`;
  2. tirar o script `duplication:semantic`;
  3. tirar a menção ao relatório no comentário do hook no `.pre-commit-config.yaml`;
  4. no shapeshifter-studio, tirar do teste a comparação com o `.jscpd-semantic.json`.

### [CSS] CSS de pacote sem `layer()` sem trava mecânica (risco aceito)

- [ ] **Severidade**: Baixa · `2026-11-16`
- **Arquivos**: `README.md` (seção "CSS só pelo `src/index.css`")
- **Descrição**: o CSS de pacote que define classe entra por `@import` no `src/index.css` com
  `layer(base)`. A regra está só escrita: se o `layer()` faltar, as classes do pacote vencem as
  utilities do Tailwind (`text-*`, `hidden`) sem aviso. Foi o defeito do `material-symbols` no
  ComicHub, o único caso nos 6 projetos.

  Decisão do PO (`2026-11-16`): **risco aceito**, sem trava, porque o custo passa do valor.
  - **Tentativa no fonte (v6.0.0):** `css/use-layers` do `@eslint/css`. Não serve:
    - o leitor do Tailwind (`tailwind-csstree` 0.4.2) quebra em `@apply px-3.5`, em
      `left-1/2`, em `bg-white/[0.02]` e no `@keyframes` dentro de `@theme`;
    - pacotes feitos de diretivas do Tailwind (`tw-animate-css`, `shadcn/tailwind.css`,
      `@welt/ui/globals.css`) não aceitam `layer()`, porque o Tailwind proíbe `@utility`,
      `@custom-variant`, `@source` e `@plugin` dentro de camada.

    O Stylelint e o Biome (`useLayeredStyles`) conferem o fonte e têm o mesmo limite.

  - **Caminho que funciona, provado nos 6 projetos (11 `index.css` compilados):** conferir o CSS
    gerado pelo build. O resultado é CSS padrão, e um leitor comum acha regra de estilo fora de
    `@layer`.
    - Pega o pacote sem `layer()`.
    - O `tw-animate-css` sai dentro de `@layer utilities`, sem exceção.
    - Custo: um plugin do Vite publicado pelo standards, mais a migração do nosso CSS (`:root`,
      `body`, `.dark`) para camada nos 5 projetos que o têm fora, o que não corrige defeito
      nenhum.

- **Sugestão**: retomar se o defeito voltar a acontecer. A versão estreita seria o plugin pelo CSS
  compilado reprovando só a regra que veio de `node_modules`, pelo mapa de origem, sem exigir que o
  nosso CSS mude.

## DX (Developer Experience)

### [ESLint] Resolver do TypeScript ignora os `tsconfig` quando o `cwd` do ESLint difere do processo

- [ ] **Severidade**: Média · `2026-10-28`
- **Arquivos**: `eslint/package.json`, `eslint/test/architecture.test.mjs`
- **Descrição**: o `eslint-import-resolver-typescript` 4.4.5 (a última versão publicada) deixa de
  usar os `tsconfig.json` (e com eles os aliases `@/…`) quando o `cwd` do ESLint é diferente do
  diretório do processo. É o que acontece na extensão ESLint do VS Code quando a pasta aberta não é
  a do `eslint.config.mjs` (num monorepo, por exemplo): os imports por alias não resolvem, e as
  regras de arquitetura (`boundaries/dependencies`) e o `import-x/no-cycle` ficam caladas no
  editor. Na linha de comando, no pre-commit e na CI (que rodam na raiz do projeto) o padrão vale
  inteiro. O teste do pacote roda com o processo na pasta do fixture por isso.
- **Sugestão**: correção upstream no `eslint-import-resolver-typescript`. A issue não foi aberta
  (decisão do PO, `2026-10-30`: só o editor é afetado; commit, CI e o Claude Code rodam da raiz e
  não são); fica o registro aqui. Quando o Renovate subir o pacote, conferir se a correção entrou e,
  se sim, rodar o teste com o processo fora da pasta do fixture. Reproduzido e corrigido numa cópia
  do 4.4.5 em `2026-10-30`. Causa, no
  `createTypeScriptImportResolver` (`src/index.ts` do `master`, L210–221): na troca de `cwd`, o
  `if (options.project)` cria um `ResolverFactory` sem `tsconfig` — o contrário da criação, que deixa
  o resolver indefinido quando há `project` —, e o `resolve()` pula a escolha do `tsconfig` por
  arquivo.

### [pre-commit] Hooks com os nomes antigos de linguagem (`system`, `script`)

- [ ] **Severidade**: Baixa · `2026-10-30`
- **Arquivos**: `.pre-commit-hooks.yaml`, `.pre-commit-config.yaml` (e o de cada projeto)
- **Descrição**: o pre-commit 4.4.0 criou `language: unsupported` e `unsupported_script` como
  nomes novos de `system` e `script`, e diz que os antigos "vão ser descontinuados". No 4.7.0 eles
  funcionam sem aviso. Trocar agora mexe nos hooks do standards e dos 6 projetos sem ganho
  (decisão do PO, `2026-10-30`: esperar).
- **Sugestão**: quando o pre-commit passar a avisar (ou o Renovate subir uma versão que avise),
  trocar os nomes no standards numa tag nova de cada hook e nos `.pre-commit-config.yaml` dos
  projetos, na mesma rodada.

### [Hooks] Mensagens de erro dos hooks Python em português

- [ ] **Severidade**: Baixa · `2026-11-05`
- **Arquivos**: `hooks/check_pyright.py`, `hooks/check_pnpm.py`, `hooks/check_pytest.py`, `hooks/check_python.py`, `hooks/dockerfiles.py`,
  `hooks/sync_base.py`, `hooks/pyproject.py`
- **Descrição**: o que os hooks escrevem no stderr/stdout (`não existe`, `não é JSON válido`, `é
regra, e regra vem da base`, `restaurado a partir do padrão`…) está em português, e a regra é
  mensagem de erro e log em inglês (comentário e docstring podem ficar em português). Achado no
  review do `check_pyright.py`; traduzir só o hook novo deixaria o repo misturado, então ficou
  registrado (decisão do PO, `2026-11-05`). Traduzir muda o que os projetos veem no terminal e as
  asserções dos testes que conferem as mensagens.
- **Sugestão**: traduzir as mensagens de todos os hooks numa mudança só, junto com os testes, e
  publicar numa tag nova de cada hook afetado (`pyright-base`, `pnpm-base`, `pytest-base` e os
  `*-base` do `sync_base.py`).
