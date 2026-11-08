# Débitos Técnicos

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
