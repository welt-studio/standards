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
  idade. Substituída em `2026-11-18`: a política é "7 dias, exceto para segurança", e vale também
  para o `security-fix`. As versões corrigidas não precisam mais esperar o `2026-11-23`.

- **Sugestão**:
  1. subir `eslint`, `typescript-eslint` e `eslint-plugin-import-x`;
  2. o `eslint-plugin-jsx-a11y-x` não tem correção: o override do `minimatch` não é à mão. O
     `security-fix` do `welt-studio/renovate` já abre o PR com ele todo dia (vermelho enquanto o
     `import-x` 4.17.1 não aceita o `minimatch` 11), e com o passo 1 o PR fica verde e faz merge;
  3. publicar a `eslint-v6.0.1` e conferir que o `pnpm audit` da CI passou. Os alertas do
     Dependabot estão desligados: a verificação é a auditoria, não o GitHub.

### [pre-commit] Projetos sem o `gitleaks-history`: segredo com `--no-verify` chega à `main`

- [ ] **Severidade**: Alta · `2026-11-18`
- **Arquivos**: nos projetos, `.pre-commit-config.yaml` e o workflow da CI
- **Descrição**: o hook `gitleaks` varre só o stage (`gitleaks git --pre-commit --staged`,
  `pass_filenames: false`). Na CI e no `pre-push` o stage está vazio, então o
  `pre-commit run --all-files` passa sem varrer nada. Reproduzido em `2026-11-18`: um commit com um
  token falso feito com `--no-verify` passou no `--all-files`. O padrão ganhou o `gitleaks-history`
  (o mesmo `rev`, `entry: gitleaks git --redact --verbose --log-opts=HEAD`, `always_run: true`,
  `stages: [manual]`), que reprova esse commit. Achado pelo /code-review do shapeshifter-studio.

  Situação em `2026-11-18`:
  - **commitado**: comichub, welt-studio, flowbit, pg-studio e nebulai;
  - em todos, o hook está verde no histórico do `HEAD`. O
    comichub e o pg-studio ganharam um `.gitleaksignore` (decisão do PO): no comichub, 4 achados
    antigos (chave do certificado de dev `CN=localhost` e a licença do lightGallery); no pg-studio,
    653 `hashed_secret` do `.secrets.baseline` do detect-secrets;
  - **shapeshifter-studio**: aplicado no working tree, fora do stage, porque os dois arquivos estão
    em stage num commit grande de outra sessão (`_ci.yml` no lugar do `standards.yml`); histórico
    limpo. Ele dizia que o `pre-push` pegava o `--no-verify`, mas no push também não há stage.

- **Sugestão**: commitar o shapeshifter depois do commit em aberto lá. O que cada projeto
  recebeu, como no standards:
  1. copiar o bloco `gitleaks-history` do `.pre-commit-config.yaml` deste repo;
  2. no workflow, `fetch-depth: 0` no `actions/checkout` e o passo
     `uv run pre-commit run --hook-stage manual gitleaks-history`;
  3. rodar o hook localmente antes do PR. Se houver achado, segredo real é rotacionado; falso
     positivo vai para o `.gitleaksignore` pelo fingerprint;
  4. no shapeshifter, corrigir também a promessa sobre o `pre-push`.

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
  conferir a cada rodada semanal se a release saiu.

### [Renovate] Merge automático sem a CI cobrir imagem Docker e docker-compose (risco aceito)

- [ ] **Severidade**: Média · `2026-11-18`
- **Arquivos**: `renovate/default.json5` (regra "Patch e minor fazem merge sozinhos"); nos projetos,
  os workflows de CI
- **Descrição**: o PO religou o merge automático de patch, minor e lockfile (`2026-11-18`) sabendo
  que o motivo que o desligou em `2026-10-23` continua em parte: a CI de alguns projetos não monta a
  imagem Docker em PR, Dockerfile de produção e docker-compose não disparam teste, e no nebulai o
  PR roda só Ruff nos arquivos alterados, Knip e audit. Custo: um patch ou minor que só quebra o
  build da imagem (o uv e o pnpm das imagens, pelos gerenciadores por regex, ou uma dependência que
  muda o que o Dockerfile copia) entra na `main` com a CI verde e quebra o deploy seguinte.
- **Sugestão**: na otimização geral da CI (combinada com o PO), cada projeto passa a montar a
  imagem e validar o docker-compose em PR que mexe neles (o pg-studio já monta desde
  `2026-11-16`), e o nebulai roda o padrão inteiro no PR. Enquanto isso não acontece, o deploy
  quebrado aparece no próprio deploy, e o PR que o causou está no histórico do Renovate.

## Arquitetura / Design

### [Python] Migração para o `python-base`: falta o shapeshifter-studio e os docs de 3 projetos

- [ ] **Severidade**: Média · `2026-11-07`
- **Arquivos**: shapeshifter-studio (`.pre-commit-config.yaml`, `.python-version`, Dockerfiles,
  `pyproject.toml`, `uv.lock`, workflows e docs); `CLAUDE.md` do flowbit, do pg-studio e do nebulai,
  e o `AGENTS.md` do nebulai
- **Descrição**: a versão do Python mora só no `python/.python-version` deste repo (decisão do PO,
  `2026-11-07`), copiada pelo hook `python-base`. Conferido no `HEAD` em `2026-11-18`: comichub,
  welt-studio, flowbit, pg-studio e nebulai têm a migração commitada, com o `.python-version` do
  pacote versionado e o `python-base` em `python-v1.1.0` e o `pnpm-base` em `pnpm-v1.1.0`. O
  comichub já não tem o passo "Dockerfiles agree with packageManager". Falta:
  - **shapeshifter-studio**: a migração inteira está no working tree, sem commit (o último commit é
    de `2026-10-19`), junto com o trabalho de outra sessão. O `HEAD` não versiona o
    `backend/.python-version`, e os Dockerfiles novos dependem dele;
  - **docs**: o `CLAUDE.md` do pg-studio e o `AGENTS.md` do nebulai ainda põem o Python entre as
    versões do próprio projeto, que o Renovate atualiza. O `CLAUDE.md` do flowbit e o do nebulai
    apontam o `.python-version` do pacote como o lugar da versão, sem dizer que ele é cópia do
    standards.

  O gerenciador regex do `uvx` no preset fica: os 5 projetos rodam `uvx pip-audit@<versão>` no
  `security-audit.yml`. A imagem da API do pg-studio, que instala pelo `requirements.txt`, é débito
  do projeto.

- **Sugestão**:
  1. shapeshifter-studio: commitar a migração **com** o `backend/.python-version` (sem ele, o build
     do deploy quebra e o `python-base` reprova na CI), depois do commit em aberto lá;
  2. corrigir os docs listados: o Python vem do standards, pelo `python-base`, e o Renovate não o
     propõe nos projetos.

### [ESLint] shapeshifter-studio ainda no CSS da v4 (migração para a `eslint-v6.1.0`)

- [ ] **Severidade**: Média · `2026-11-16`
- **Arquivos**: shapeshifter-studio, `frontend/package.json`, `frontend/src/main.tsx` e
  `frontend/src/index.css`
- **Descrição**: na v5 (decisão do PO, `2026-11-16`), todo CSS de pacote entra por `@import` no
  `src/index.css`, e o `main.tsx` importa só o `./index.css`. O que a v4 aceitava reprova. A v6.1.0
  tem as mesmas regras da v5, sem o lint de CSS da v6.0.0. Conferido no `HEAD` em `2026-11-18`:
  comichub, welt-studio, flowbit, pg-studio e nebulai estão na `eslint-v6.1.0`, commitada. O
  shapeshifter-studio tem a subida só no working tree, sem commit.
- **Sugestão**: commitar a subida do shapeshifter-studio depois do commit em aberto lá, com o CSS
  de pacote fora do `main.tsx`, entrando por `@import` no `index.css` (com `layer(base)` no que
  define classe).

### [jscpd] shapeshifter-studio ainda com o relatório semântico (migração para a `jscpd-v2.0.0`)

- [ ] **Severidade**: Baixa · `2026-11-17`
- **Arquivos**: shapeshifter-studio, `.pre-commit-config.yaml` (`rev` do `jscpd-base`),
  `.jscpd-semantic.json`, `frontend/package.json` (script `duplication:semantic`) e
  `backend/tests/test_jscpd_config.py`
- **Descrição**: decisão do PO (`2026-11-17`): sai o relatório semântico do jscpd, que rodava um
  modelo de embeddings sobre o código. A `jscpd-v2.0.0` deixa de gerar o `.jscpd-semantic.json`, mas
  não apaga a cópia que já está no projeto. Conferido no `HEAD` em `2026-11-18`: comichub,
  welt-studio, flowbit, pg-studio e nebulai estão na `jscpd-v2.0.0`, sem a cópia e sem o script. No
  shapeshifter-studio, o `HEAD` ainda tem os três, e a subida está só no working tree.
- **Sugestão**: no commit da subida do shapeshifter-studio, apagar o `.jscpd-semantic.json`, tirar o
  script `duplication:semantic` e tirar do teste a comparação com o `.jscpd-semantic.json`.

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
