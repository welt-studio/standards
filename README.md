# Standards

Os padrões de desenvolvimento da Welt Studio (lint, tipos, formatação, duplicação, testes,
dependências Python, scripts de instalação do pnpm e a política de versões do Renovate), declarados
uma vez para todos os projetos.

## Desenvolver este repo

O standards segue o padrão que publica, com os mesmos hooks dos projetos
(`.pre-commit-config.yaml`); os hooks `*-base` rodam os scripts deste working tree, e
as cópias que eles geram na raiz (`ruff-base.toml`, `pyright-base.json`, `.prettierignore`,
`.jscpd*.json`) não se editam.

| Parte                                       | Onde                                                                                                                                    |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Scripts dos hooks (stdlib, sem dependência) | `hooks/`; testes em `tests/` (os dois em strict no Pyright)                                                                             |
| Ferramentas do Python                       | `pyproject.toml` da raiz (grupo `dev`), só ambiente de desenvolvimento: `uv sync`                                                       |
| Pacotes publicados                          | `eslint/`, `prettier/`, `tsconfig/`, `vitest/`, num workspace pnpm na raiz; o `package.json` da raiz é só o ambiente de desenvolvimento |

```sh
uv sync && pnpm install
uvx pre-commit@4.7.0 install   # os três ganchos vêm do `default_install_hook_types`
uv run pytest                  # testes dos hooks, com a cobertura e o piso (`--cov` no `addopts`)
pnpm test                      # testes dos pacotes (ESLint, Prettier, tsconfig, Vitest)
```

O workflow `Test` roda os hooks no repo inteiro e os testes em todo push e PR, como o padrão de
pre-commit dos projetos (abaixo) pede.

Os débitos do próprio standards ficam em `docs/TECH_DEBT.md`.

## Pre-commit: o padrão dos projetos

O `.pre-commit-config.yaml` deste repo é a referência para o dos projetos. Além dos hooks de cada
padrão (seções abaixo), todo projeto tem:

```yaml
# Os três ganchos num `uvx pre-commit@4.7.0 install` só, sem flag. A lista substitui o padrão do
# pre-commit: sem o `commit-msg`, o conventional-pre-commit nunca é instalado.
default_install_hook_types: [pre-commit, commit-msg, pre-push]
# Sem isto, todo hook vale para todos os ganchos instalados e os do commit rodam de novo na mensagem
# e no push. Quem precisa de outro estágio declara `stages:`.
default_stages: [pre-commit]

repos:
  # Testes no push, não no commit (`stages: [pre-push]`): pytest e vitest com a cobertura e o piso.
  # Teste vermelho ou cobertura abaixo do piso barram o push (decisão do PO). Cada suíte filtra pela
  # pasta dela (`files:`): push que só toca o backend não roda o vitest, e vice-versa; a CI roda tudo.
  - repo: local
    hooks:
      # `--directory`, não `--project`: o pytest acha o `[tool.pytest]` pela pasta em que roda. Da
      # raiz, com `--project`, ele roda sem a config (sem strict, sem rede bloqueada, sem cobertura).
      - id: pytest
        entry: uv run --directory backend pytest -q
        language: system
        files: ^backend/
        pass_filenames: false
        stages: [pre-push]
      - id: vitest
        entry: pnpm --filter frontend run test:coverage
        language: system
        files: ^frontend/
        pass_filenames: false
        stages: [pre-push]
  # Repos de terceiros fixados por SHA, com a versão no comentário (`pre-commit autoupdate --freeze`):
  # uma tag pode ser movida para outro código, um SHA não.
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: 3e8a8703264a2f4a69428a0aa4dcb512790b2c8c # frozen: v6.0.0
    hooks:
      - id: mixed-line-ending
        args: [--fix=lf]
      - id: check-case-conflict
      # ... os outros básicos (ver o `.pre-commit-config.yaml` deste repo)
```

- **Básicos** (`pre-commit-hooks`): espaço no fim de linha, fim de arquivo, `check-yaml`/`json`/`toml`,
  arquivo grande, marcador de conflito, chave privada, fim de linha `lf` (`mixed-line-ending
--fix=lf`, como o Ruff e o Prettier) e dois arquivos que só diferem na caixa
  (`check-case-conflict`, que quebra o checkout no macOS e no Windows). Mais o gitleaks e o
  conventional-pre-commit (`stages: [commit-msg]`).
- **SHA com `# frozen: vX.Y.Z`** nos repos de terceiros. O gerenciador `pre-commit` do Renovate
  (ligado pelo `:enablePreCommit` do preset) lê essa forma e atualiza o SHA e o comentário juntos.
- **Testes no `pre-push`**: pytest (com `--cov` no `addopts`, ver "Testes (pytest)") e vitest
  (`vitest run --coverage`). O commit fica rápido; o push não sobe teste vermelho.
- **CI**: `uvx pre-commit@4.7.0 run --all-files --show-diff-on-failure` (todo hook do commit no repo
  inteiro) e os testes com cobertura (`uv run pytest`, `pnpm run test:coverage`), como o
  `.github/workflows/test.yml` deste repo. A versão do pre-commit no `uvx` dos workflows, do
  `.pre-commit-config.yaml` e do README sobe pelo Renovate, todas no mesmo PR.

## ESLint: `@welt-studio/eslint-config`

Pacote em `eslint/`, instalado por tag do git (o repositório é público, então nenhum ambiente
precisa de token: máquina, CI e build Docker baixam como qualquer pacote):

```json
"@welt-studio/eslint-config": "github:welt-studio/standards#eslint-v4.3.2&path:/eslint"
```

O lockfile guarda o commit exato da tag. Atualizar um projeto é trocar a tag e rodar `pnpm install`;
o Renovate abre esse PR sozinho quando sai uma tag nova, já com o lockfile (ver "Renovate").

```javascript
// eslint.config.mjs
import { weltConfig } from "@welt-studio/eslint-config";

export default weltConfig({
  tsconfigRootDir: import.meta.dirname,
  files: ["src/**/*.{ts,tsx}"], // com tipo (o que o tsconfig inclui)
  framework: "vite", // app Vite; sem ele, pacote/biblioteca (globais do Node)
  query: true, // usa TanStack Query
  i18n: true, // produto traduzido
});
```

**O padrão é o mesmo em todos os projetos, e não existe regra exclusiva de projeto.** O arquivo do
projeto só declara onde estão os arquivos e o que o projeto é (framework, TanStack Query,
traduzido); limite, regra e plugin vêm daqui. Precisou de uma regra nova? Ela entra neste pacote,
para todos, numa versão nova.

`files` e `untypedFiles` não podem se sobrepor: um arquivo é lintado com tipo (está num `tsconfig`)
ou sem tipo (scripts, configs de ferramenta, `.mjs`). Os sem tipo (padrão `**/*.{js,jsx,mjs,cjs}`)
recebem o padrão inteiro menos as regras que exigem tipo, com os globais do Node.

`weltConfig` aplica, nesta ordem:

| Bloco                                                            | O que pega                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `typescript-eslint` `strictTypeChecked` + `stylisticTypeChecked` | promise sem `await`/`catch`, `async` onde se espera retorno síncrono, `any` vazando, condição sempre verdadeira                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `@eslint-react/eslint-plugin` (`recommended-type-checked`)       | key ausente ou instável, contexto recriado a cada render, API do React usada errado (substitui o `eslint-plugin-react`, parado no ESLint 9). As regras que repetem as do plugin de hooks ficam só lá                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `eslint-plugin-react-hooks` (`recommended-latest`)               | regras dos hooks e do React Compiler                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `eslint-plugin-jsx-a11y-x` (`recommended`)                       | acessibilidade (fork do `jsx-a11y` que suporta ESLint 10)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `framework: "vite"`                                              | no código do app, globais do navegador e Fast Refresh (`eslint-plugin-react-refresh`); configs de ferramenta (`*.config.ts`) ficam com os globais do Node. Liga também a arquitetura do app (`eslint-plugin-boundaries`, ver "Arquitetura do front"). Next não é suportado: os apps são Vite                                                                                                                                                                                                                                                                                                                                                           |
| `@tanstack/eslint-plugin-query` (`query: true`)                  | chave de query incompleta, `QueryClient` instável                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `eslint-plugin-i18next` (`i18n: true`)                           | texto visível escrito direto no JSX (entre tags ou em qualquer atributo) ou num toast (`toast("…")`, `toast.error("…")`, `description`, `toast.promise`). Ficam de fora só os atributos e chaves de objeto que são código — rota (`href`, `to`), `data-*`, `testId`, ícone (`name`, `icon`), classe (`className`, `classNames`, `cn(...)`), cor, `aria-hidden`, SVG, `type` —, locale e formato (`toLocaleString`, `Intl.*`), `toast.dismiss(id)` e os testes. Prop nova é cobrada até entrar nessa lista: erro a mais aparece, erro a menos passa calado. Vale para qualquer biblioteca de tradução, e o padrão dos projetos traduzidos é o `i18next` |
| `eslint-comments` + `linterOptions`                              | `eslint-disable` de arquivo inteiro, sem regra ou sem motivo (`-- motivo`), e diretiva que não desliga nada                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Tamanho, complexidade e boas práticas                            | `complexity` 12, função 80 linhas, arquivo 400, `max-statements` 30, `max-params` 5, `max-depth` 4, `max-nested-callbacks` 3, boas práticas                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Regras com tipo além do `strict`                                 | `switch` sobre união que esquece um caso (`switch-exhaustiveness-check`), sombra de variável, retorno inconsistente, `readonly` onde cabe, método como propriedade (`method-signature-style`), `sort()` sem comparador, import/export de tipo marcado como tipo                                                                                                                                                                                                                                                                                                                                                                                        |
| Imports (`eslint-plugin-import-x`)                               | ciclo de import (resolvendo os aliases do `tsconfig`), import duplicado, import de si mesmo, caminho com segmento inútil e a ordem (biblioteca padrão, pacotes, código do projeto, um grupo por bloco, como o `I` do Ruff). Os aliases resolvem pelos `tsconfig.json` versionados no git a partir do `tsconfigRootDir`, um por app num monorepo; um `tsconfig.json` ainda sem `git add` fica invisível, e os imports por alias dele passam sem `no-cycle` e sem arquitetura até ser versionado                                                                                                                                                         |
| O que o git ignora                                               | todo arquivo que o git ignora (`.gitignore` de qualquer pasta, `.git/info/exclude`) fica fora do lint, consultado no próprio git a partir do `tsconfigRootDir`: o lint local vê o mesmo que a CI. O que está no git e não é nosso (saída de gerador, como o `routeTree.gen.ts` do TanStack Router e as migrations, e código de terceiros, em `vendor/` ou minificado) também fica fora, pela lista comum de ignores do padrão (ver "Ignores comuns"). O `ignores` do projeto fica só para o que está no git e não deve ser lintado (código gerado ou de terceiros versionado)                                                                          |
| Comentários                                                      | espaço depois de `//`, frase em maiúscula (menos quando começa com nome de código, como `hydrateRoot`), nenhum `TODO:`/`FIXME`/`HACK:` no código (vão para o débito técnico, parking lot ou roadmap)                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Testes (`*.test.ts(x)` ao lado do código, `e2e/`)                | sem limites de tamanho; o resto do padrão vale. Nos unitários, `@vitest/eslint-plugin` (`it.only` esquecido, teste sem `expect`, `expect` condicional), `eslint-plugin-testing-library` (query certa, sem `container`) e `eslint-plugin-jest-dom` (matcher no lugar de comparar booleano)                                                                                                                                                                                                                                                                                                                                                              |
| Prettier (`eslint-plugin-prettier`)                              | formatação como regra, por último, com a config do projeto (o `@welt-studio/prettier-config`); `curly` religado depois dele                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

**Não há aviso:** toda regra é erro ou está desligada (os projetos rodam com `--max-warnings=0`, e
um aviso já reprovaria).

O pacote exporta só `weltConfig` (com tipos em `index.d.ts`): não há regra solta para reaplicar,
porque reaplicar pedaço do padrão é montar uma versão parcial dele.

`eslint` (10), `@eslint/js` (10), `typescript` (6), `typescript-eslint` e `prettier` (3) são
`peerDependencies`: a versão é a do projeto, e o padrão exige essas majors. Os plugins vêm com o
pacote, em versão fixa — o projeto não declara nem registra nenhum deles.

### Arquitetura do front

Todo app Vite (`framework: "vite"`) segue a mesma estrutura em `src/`, com a direção dos imports
travada pelo `eslint-plugin-boundaries` (decisão do PO, 2026-10-27). As regras são as do
[bulletproof-react](https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md),
e as rotas são as rotas por arquivo do TanStack Router, finas como no
[shadcn-admin](https://github.com/satnaing/shadcn-admin):

```
src/
  main.tsx                 # monta o app; importa o index.css
  index.css                # o CSS global (tema, fontes): uma porta de entrada, que importa os outros
  entry-server.tsx         # só com prerender SSR (`vite build --ssr`)
  vite-env.d.ts
  app/                     # providers, instância do router, layout global, error boundary
  routes/                  # rotas por arquivo do TanStack Router (`createFileRoute`)
  routeTree.gen.ts         # gerado pelo @tanstack/router-plugin
  features/<nome>/         # um domínio: api/ components/ hooks/ stores/ types/ utils/ (só as que usa)
  components/  hooks/  lib/  stores/  types/  utils/  config/  assets/  testing/   # a base
```

| Camada                                                                                                               | Importa                                             |
| -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| arquivos de entrada da raiz de `src/` (`main.tsx`, `entry-server.tsx`, `routeTree.gen.ts`, `vite-env.d.ts`) e `app/` | tudo                                                |
| `routes/`                                                                                                            | rotas, features e a base                            |
| `features/<nome>/`                                                                                                   | a própria feature e a base, **nunca outra feature** |
| a base                                                                                                               | só a base                                           |

- **Feature não conhece feature.** Quem junta duas é a rota ou o `app/`; o que duas usam sobe para a
  base. A página da feature fica em `features/<nome>/components/<nome>-page.tsx`, e a rota a importa
  direto: sem `index.ts` que só reexporta, que o bulletproof desaconselha (atrapalha o tree shaking
  do Vite).
- **Pasta ou arquivo de `src/` fora da lista reprova** (`boundaries/no-unknown-files`): a estrutura
  é a mesma em todos os apps. Na raiz de `src/` só ficam os arquivos de entrada da tabela e o
  `index.css`; `App.tsx` e `router.tsx` moram em `app/`.
- **CSS global:** um `src/index.css`, importado pelo `main.tsx`, como no bulletproof. Ele é parte da
  entrada, não de uma camada; `assets/` é para arquivo estático (imagem, fonte). Tema e fontes em
  arquivos separados entram pelo `index.css`. O ESLint não lê CSS, então esta regra fica escrita, sem
  trava.
- **Rota fina:** arquivo em `src/routes/` tem no máximo 60 linhas. Ele só declara o `createFileRoute`
  (parâmetros, busca com zod, loader, guarda) e o componente vem da feature.
- **Teste fica ao lado do código** e importa da própria feature e de `testing/`.
- Pacote e biblioteca (sem `framework`) não têm essa estrutura: não têm rota nem feature.

Os padrões casam pela direita, então valem igual com o app na raiz do projeto ou num monorepo
(`apps/admin/src/...`).

**No editor, a arquitetura pode ficar calada.** O `eslint-import-resolver-typescript` 4.4.5 deixa de
usar os `tsconfig.json` (e com eles os aliases `@/…`) quando o `cwd` do ESLint difere do diretório
do processo, como na extensão ESLint do VS Code com uma pasta aberta que não é a do
`eslint.config.mjs`. Aí os imports por alias não resolvem, e o `boundaries/dependencies` e o
`import-x/no-cycle` não acusam nada no editor. Na linha de comando, no pre-commit e na CI o padrão
vale inteiro. A saída é a correção upstream (débito em `docs/TECH_DEBT.md`).

### Ignores comuns

O que está no git e não é nosso para lintar, formatar ou acusar — saída de gerador (`**/*.gen.ts`,
`**/migrations/**`, `**/alembic/versions/**`) e código de terceiros (`**/vendor/**`, `**/*.min.js`,
`.mjs`, `.cjs` e `.css`) — é uma lista só para todas as ferramentas, declarada em
`eslint/ignores.json`. Ela mora no pacote de ESLint porque ele a lê em runtime, e o projeto instala
só a pasta `eslint/`. O Prettier (`prettier/ignore`), o jscpd (`jscpd/*.json`), o Ruff
(`extend-exclude`) e o Pyright (`ignore`) leem a lista em arquivo próprio, no formato deles: o
`tests/test_ignores.py` reprova se alguma divergir da declaração (fora o que é só de uma
ferramenta, como os lockfiles do Prettier e os testes do relatório semântico do jscpd). Padrão novo
entra no `ignores.json` e em cada cópia, numa tag de cada pacote.

### Publicar uma versão

1. Mudar `eslint/`, subir `version` no `eslint/package.json`.
2. `pnpm test` na raiz: o fixture (`eslint/test/fixture/`, um monorepo mínimo) roda o padrão como
   um projeto que instala o pacote (montado só com o que o `files` do `eslint/package.json` publica)
   e confere o que cada arquivo reprova: feature importando feature, base importando feature, pasta
   fora da estrutura, rota grossa e ciclo que só passa por alias. Regra nova da arquitetura ganha
   caso no fixture, e módulo novo do pacote entra no `files`. O workflow `Test` roda o mesmo em todo
   push e PR, inclusive nos do Renovate que sobem os plugins.
3. Commit e tag `eslint-vX.Y.Z` no mesmo commit, push da tag.
4. O Renovate abre em cada projeto o PR que troca a tag, com o lockfile; revisar e fazer o merge.

## Ruff: `ruff/base.toml` pelo hook `ruff-base`

O `extend` do Ruff só lê arquivo local (sem URL nem pacote), então o padrão chega ao projeto como
cópia, mantida por um hook de pre-commit deste repo (`hooks/check_ruff.py`, que copia pelo
`hooks/sync_base.py`). Depois ele reprova o que desligaria a base sem aparecer nela:

- em toda config de Ruff versionada no projeto (`ruff.toml`, `.ruff.toml`, o `[tool.ruff]` de um
  `pyproject.toml`, mesmo vazio, fora a lista comum de ignores): sem `extend` que chegue à cópia
  (direto ou por outra config do projeto), `select` próprio (regra a mais entra pelo
  `extend-select`), `exclude`/`extend-exclude`/`include`/`lint.exclude` (tirar arquivo do Ruff é da
  lista comum de ignores, não do projeto), uma regra protegida desligada por
  `ignore`/`per-file-ignores` (pelo código, por um prefixo ou pelo `ALL`) e `banned-api` redefinido
  sem os itens da base (a tabela do projeto substitui a da base inteira). As regras protegidas são o
  `TID251` (`Any` e `cast`) e o `PGH004` (sem ele, o `noqa` sem código calaria o `TID251`);
- nos `.py`, `.pyi` e `.ipynb` versionados, o `noqa` que desliga uma regra protegida na linha e o
  `noqa` de arquivo (`ruff: noqa`, `flake8: noqa`) sem códigos ou com uma delas.

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/welt-studio/standards
  rev: ruff-v2.1.0
  hooks:
    - id: ruff-base
    - id: ruff
      args: [backend] # a pasta do pacote Python (obrigatória; `.` quando é a raiz)
    - id: ruff-format
      args: [backend]
```

O hook escreve `ruff-base.toml` na raiz do projeto, igual ao `ruff/base.toml` do `rev`. Se a cópia
diverge (editada à mão, ou o `rev` mudou), ele a reescreve e reprova o commit uma vez, como um
formatter. A versão do padrão fica só no `rev`.

```toml
# <pacote>/ruff.toml
extend = "../../ruff-base.toml" # caminho até a raiz do projeto

[lint.isort]
known-first-party = ["app"]
```

**Os hooks `ruff` e `ruff-format` também vêm daqui** (`hooks/run_python_tool.py`), não do projeto:
uma declaração só do comando e do filtro, que muda para todos numa tag nova. Eles rodam o Ruff do
projeto (a versão do `uv.lock` dele) nos `.py`, `.pyi` e `.ipynb` do commit que estão no pacote. O
commit que muda uma config (`ruff-base.toml`; o `ruff.toml`, o `.ruff.toml` ou o `[tool.ruff]` de um
`pyproject.toml` do pacote, inclusive de uma subpasta) ou o `uv.lock` (a versão do Ruff) roda no
pacote inteiro: o arquivo está no commit, mas o efeito dele cai em todo arquivo, e sem isso a regra
nova só aparecia na CI. O `pyproject.toml` sem `[tool.ruff]` (dependência que subiu) não dispara.

**O hook roda de dentro do pacote** (`uv run --directory <pacote>`, com os caminhos relativos a ele),
como a CI. Rodando da raiz com o arquivo pelo nome, o Ruff decide as exclusões (`extend-exclude` +
`force-exclude`) com a config padrão dele, e não com a do pacote: migrations e `vendor/` seriam
conferidos e corrigidos no commit. Passar `--config` resolveria as exclusões, mas faria o Ruff
ignorar a config de uma subpasta (`tests/ruff.toml` com `extend` da do pacote).

**O padrão é o mesmo em todos os projetos.** O `ruff.toml` do pacote só declara fatos do projeto:
`known-first-party` e, em `extend-exclude` (que soma com o do base), código gerado fora das pastas
que o base já exclui. Regra, limite e exceção vêm do base; precisou de regra nova, ela entra aqui,
para todos, numa tag nova.

| Bloco                          | O que fixa                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `required-version`             | a versão mínima do Ruff, a primeira que conhece todas as regras do padrão. A exata é a do `uv.lock` do projeto. Sem `preview`, porque uma versão patch do Ruff pode mudar o que está em preview                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `select` explícito (sem `ALL`) | a união das famílias que os projetos usavam: pycodestyle, pyflakes, isort, naming, pyupgrade, bandit, bugbear, pylint, async, timezone, pathlib, Ruff, tryceratops, logging (`LOG`), concatenação de string (`ISC001`/`ISC003`/`ISC004`), anotações, `TC`, FastAPI, Django, `noqa` sem código (`PGH004`) e sem uso (`RUF100`), `# type: ignore` sem o código da regra (`PGH003`). Desde a `ruff-v1.5.0`, também: estilo do pytest (`PT`), `breakpoint()` esquecido (`T10`), NumPy (`NPY`), `raise` (`RSE`), f-string (`FLY`), import relativo que sobe pasta (`TID252`) e mensagem de exceção numa variável (`EM`). Sem `INP`: as pastas que ela acusa (`tests/`, `scripts/`, `alembic/`) não são pacote de propósito, e o pytest no modo `importlib` não pede `__init__.py`. Sem `FA`: `from __future__ import annotations` é proibido (Python 3.14, PEP 649); `freezegun` também (relógio em teste é o `time-machine`). Desde a `ruff-v2.0.0`, o `TID251` proíbe também `Any` e `cast` (`typing`, `typing_extensions` e o `_typeshed.Incomplete`), testes incluídos: ver "Sem contorno de tipo" no Pyright |
| Limites                        | complexidade 12 (igual ao ESLint), `max-args` 5, `max-branches` 12, `max-returns` 6, `max-statements` 30 (igual ao ESLint)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Segurança e defaults           | senha escrita no código (`S105`/`S106`) e chamada em default de argumento (`B008`) ligadas; o `Depends`, `Query`, `Path`, `Body`, `Header`, `Cookie`, `Form`, `File` e `Security` do FastAPI são liberados no `extend-immutable-calls`, que é como o FastAPI declara dependência e parâmetro de rota                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| Runtime                        | `TC001`–`TC003` desligadas: no Python 3.14 mover import "só de tipo" para `TYPE_CHECKING` quase não ganha nada, e Pydantic, SQLAlchemy e FastAPI leem anotações em runtime. Fica o contrário (`TC004`: import de runtime escondido em `TYPE_CHECKING`), com Pydantic e rotas do FastAPI marcados como runtime                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| isort                          | `alembic` sempre de terceiros (`known-third-party`): a pasta `alembic/` das migrations o fazia mudar de grupo conforme a pasta em que o Ruff roda; o projeto declara só o `known-first-party` dele                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Exceções padrão                | testes (assert, número mágico, senha de fixture, fixture, tamanho); `@declared_attr` do SQLAlchemy como classmethod; os ignores comuns (migrations geradas, `vendor/`, minificados) ficam fora do lint e do format (`extend-exclude` + `force-exclude`), como no Prettier e no jscpd                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `[format]`                     | aspas duplas, espaço, `lf`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

A versão do Ruff mora só no `uv.lock` do projeto: os hooks daqui chamam o `uv run`, não instalam
o Ruff.

### Publicar uma versão do padrão

1. Mudar `ruff/base.toml` (ou os hooks `ruff`/`ruff-format`). O `required-version` só sobe quando o
   padrão passa a usar uma regra que a versão mínima atual não conhece.
2. Commit e tag `ruff-vX.Y.Z` no mesmo commit, push da tag.
3. O Renovate troca o `rev` dos hooks `ruff-base`, `ruff` e `ruff-format` em cada projeto, no PR
   mensal.

### Subir o Ruff num projeto

É só o projeto: o pin `ruff==` do `pyproject.toml` e o `uv.lock`, sem tag aqui, e o Renovate faz
isso no PR mensal. O Ruff novo pode mudar o resultado do lint ou do format (as versões minor
promovem regras e mudam o estilo estável), e isso aparece na CI do próprio PR.

## Renovate: `renovate/default.json5`

A política de versões de todos os projetos, declarada uma vez. Cada projeto só a herda, com um
`renovate.json` na raiz. O Renovate roda no workflow do repositório privado `welt-studio/renovate`,
com um GitHub App da organização e saída de rede restrita a uma lista de domínios; nenhum serviço
de terceiros recebe o código:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["github>welt-studio/standards//renovate/default.json5"]
}
```

O preset é lido do `main`, sem tag: mudar a política aqui vale para todos no merge.

| Regra            | O que faz                                                                                                                                                                                                                                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Calendário       | uma rodada por mês, na madrugada do dia 1 (`America/Sao_Paulo`), com a manutenção do lockfile junto                                                                                                                                                                                               |
| Idade mínima     | a versão mais nova com pelo menos 7 dias de publicada; sem data no registro, fica retida. A trava do pnpm (`minimumReleaseAge` do `pnpm-workspace.yaml`) continua na instalação                                                                                                                   |
| Agrupamento      | um PR por projeto com tudo que não é major; cada major no seu                                                                                                                                                                                                                                     |
| Merge            | todo PR espera a aprovação do PO. O merge automático está desligado até a CI dos projetos montar as imagens Docker em PR e testar o que cada PR muda (o motivo e como religar estão no preset)                                                                                                    |
| PR separado      | majors, minor do Python (depende de wheel do `torch`), major de Node e pnpm, e cada um dos pacotes deste repo (`@welt-studio/eslint-config`, `tsconfig`, `prettier-config` e `vitest-config`), com o lockfile                                                                                     |
| Segurança        | correção de vulnerabilidade (alerta do GitHub) abre PR na hora, fora do calendário e sem a idade mínima, todas num PR só por projeto (correções que dependem umas das outras resolvem o lockfile juntas). Correção do npm com menos de 7 dias ainda precisa do `minimumReleaseAgeExclude` do pnpm |
| Actions          | fixadas por SHA, com a versão num comentário                                                                                                                                                                                                                                                      |
| Fora do Renovate | os `overrides` do pnpm (correção de vulnerabilidade com faixa fechada) e o `rustsec/audit-check`, preso no commit do `main` até sair release em Node 24                                                                                                                                           |

Os gerenciadores do Renovate leem sozinhos `package.json` (inclusive `packageManager` e
`devEngines`), o `catalog` do pnpm, `pyproject.toml` e `uv.lock`, `.python-version`, Dockerfiles,
docker-compose, workflows e o `.pre-commit-config.yaml` (inclusive o `rev` fixado por SHA com
`# frozen: vX.Y.Z`, que ele atualiza junto com o comentário). O preset acrescenta, por regex, o que
eles não leem: o `[tool.uv] required-version`, as imagens `ghcr.io/astral-sh/uv` e
`ghcr.io/pnpm/pnpm` (o GHCR não informa data, então andam pela versão do pacote no PyPI e no npm), o
`uvx <ferramenta>@<versão>` dos workflows, do `.pre-commit-config.yaml` e do README, o
`pnpm dlx --package <pacote>@<versão>` do README e os pacotes deste repo pela tag de cada um
(`eslint-v*`, `tsconfig-v*`, `prettier-v*`, `vitest-v*`). Esses pacotes chegam com o lockfile: o preset roda
`pnpm install --lockfile-only --ignore-scripts` no PR, o único comando que o runner permite
(`allowedCommands`), que recalcula o lockfile sem rodar código de pacote.

Duas regras ainda existem só por um projeto, cada uma com o débito que a tira no TECH_DEBT dele: o
`ARG PNPM_VERSION` (comichub, que deve usar o `FROM` direto como os outros) e o `UV_VERSION` do
instalador do nebulai (que deve ler o `required-version`). Regra nova no preset vale para todos;
versão escrita num lugar que só um projeto usa se corrige no projeto, não aqui.

Conferir uma mudança no preset antes do merge (pelo pnpm: o `devEngines` deste repo recusa o `npx`):
`pnpm dlx --package renovate@44.176.0 renovate-config-validator --no-global renovate/default.json5`.

## Pyright: `pyright/base.json` pelo hook `pyright-base`

O mesmo esquema do Ruff: o `extends` do Pyright só lê arquivo local, e o hook mantém a cópia na raiz
do projeto (o `hooks/check_pyright.py` copia pelo mesmo `hooks/sync_base.py` do Ruff). Depois ele
reprova o que contornaria a base: no `pyrightconfig.json`, qualquer chave além dos fatos do projeto
(caminhos, ambiente, versão do Python, `executionEnvironments` com `root`/`extraPaths`) ou um
`extends` que não seja a cópia; nos `.py` e `.pyi` do git que o Pyright analisa (o
`include`/`exclude` do projeto, fora o `ignore` da base), o comentário `# pyright: <modo ou regra>`
e tudo o que cala um erro em vez de corrigi-lo: todo `# type: ignore` e todo `# pyright: ignore` fora
o marcador de lib sem stubs publicados (`# pyright: ignore[reportMissingTypeStubs]` no import). O
`noqa` que fura o `TID251` é do hook `ruff-base`. Pasta passada em `args` quando o
`pyrightconfig.json` não está na raiz.

**Sem contorno de tipo** (decisão do PO, 2026-11-05): `Any` e `cast` são proibidos pelo `TID251` do
padrão Ruff, testes incluídos; dado dinâmico (JSON, TOML, payload) é `object` (ou
`dict[str, object]`) estreitado com `isinstance` ou validado. Ignorar o erro é proibido pelo hook. O
que nenhuma ferramenta pega, e o review cobra: renomear para escapar de regra (a variável
`PASSWORD_…` que vira `CREDENTIAL_…` para o `S105` não ver), em vez de corrigir ou de marcar o falso
positivo com `noqa` e o motivo.

**Bibliotecas de terceiros:** o Pyright penaliza o nosso código, não a lib. Lib com pacote de stubs
mantido tem o pacote no grupo `dev` (o `reportMissingTypeStubs` reprova até ele entrar); lib sem
stubs publicados leva o marcador acima em cada import dela, que sai sozinho quando um pacote de stubs
for instalado (o `reportUnnecessaryTypeIgnoreComment` o reprova). Fora isso, não se escreve stub,
cast nem ignore para compensar tipo de lib.

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/welt-studio/standards
  rev: pyright-v3.1.0
  hooks:
    - id: pyright-base
    - id: pyright
      args: [backend] # a pasta do pacote Python (obrigatória; `.` quando é a raiz)
      # pass_filenames: false # projeto sem fila do strict: o projeto inteiro em todo commit
```

O hook `pyright` também vem daqui (`hooks/run_python_tool.py`): roda o Pyright do projeto
(`uv run --project <pacote> pyright`, da raiz) nos `.py` e `.pyi` do commit que o
`pyrightconfig.json` analisa: o da raiz, ou o do pacote quando a raiz não tem (o Pyright recebe
`--project <pacote>`). O commit que muda o `pyrightconfig.json`, o `pyright-base.json` ou o `uv.lock`
(a versão do Pyright, os stubs) roda no projeto inteiro.

```jsonc
// pyrightconfig.json, na raiz do projeto: só fatos dele
{
  "extends": "./pyright-base.json",
  "include": ["backend"],
  "venvPath": "backend",
  "venv": ".venv",
}
```

| Bloco                                | O que fixa                                                                                                                                                                                                                                                         |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `typeCheckingMode`                   | `strict` em tudo, testes incluídos. A anotação de parâmetro e de retorno é do `ANN` do Ruff, que não vale nos testes                                                                                                                                               |
| `reportUnknown*`                     | a família toda desligada (`Member`, `Argument`, `Variable`, `Parameter`, `Lambda`): o `Unknown` das bibliotecas mal tipadas reprovava cada linha que as tocava. O Pyright não separa o da biblioteca do nosso: `items = []` que recebe qualquer coisa também passa |
| `reportPrivateUsage`                 | desligada: acesso a privado é do Ruff (`SLF001`), que o cobra no código e o libera nos testes                                                                                                                                                                      |
| `reportMissingParameterType`         | desligada: parâmetro sem anotação é do Ruff (`ANN001`-`ANN003`), que o cobra no código e o libera nos testes. A fixture do pytest é injetada pelo nome, e o teste roda inteiro a cada suíte: um tipo errado ali já falha no pytest                                 |
| `enableTypeIgnoreComments`           | `false`: o `# type: ignore` não vale (o erro continua aparecendo), e o hook reprova o comentário                                                                                                                                                                   |
| `reportUnnecessaryTypeIgnoreComment` | o marcador `# pyright: ignore[reportMissingTypeStubs]` que não ignora nada reprova: a lib ganhou stubs, e o marcador sai                                                                                                                                           |
| `ignore`                             | os ignores comuns (migrations geradas, `vendor/`, minificados) não são acusados (como no Ruff, no Prettier e no jscpd); quem os usa continua conferido contra os tipos deles. O projeto não declara `ignore`, que substituiria este                                |

O projeto não declara `strict` nem põe `# pyright: strict` num arquivo: no Pyright, os dois religam
toda regra do strict (nas pastas da lista, ou no arquivo), inclusive as `reportUnknown*` que a base
desliga; o hook reprova os dois. Projeto que vem da v1 apaga a lista; os testes passam a ser
cobrados pelo resto do strict (genérico sem argumento no `reportMissingTypeArgument`, a inferência
estrita de `list`/`dict`/`set`, lib sem stubs no `reportMissingTypeStubs`).

Nenhuma outra regra desligada: o projeto não declara `report*`. A versão do Pyright é o pin do
`pyproject.toml` de cada projeto, que o Renovate sobe. O hook do projeto checa os arquivos do commit
(a fatia que se commita); a CI checa o projeto inteiro e fica vermelha até a fila zerar, porque um
contrato quebrado aparece em quem chama a função, fora do commit. Os arquivos do commit são o
ponto de partida enquanto o projeto tem fila: checar tudo no commit reprovaria todo commit pelos
erros que já existem. Projeto sem fila passa a checar o projeto inteiro também no hook
(`pass_filenames: false` no hook `pyright`), como o próprio standards, que já está em zero.

**Projeto Django:** os stubs do Django são os do `django-types`, feitos para o Pyright. O
`django-stubs` depende do plugin do mypy, e sem ele todo campo de model sai `Unknown`. Os stubs do
DRF continuam os do `djangorestframework-stubs` (o `djangorestframework-types` está parado e perde o
tipo genérico do serializer). Como este puxa o `django-stubs` por dependência, e os dois se instalam
na mesma pasta, o `pyproject.toml` o exclui:

```toml
[tool.uv]
exclude-dependencies = ["django-stubs", "django-stubs-ext"]
```

No comichub, a troca levou o Pyright de 2374 para 1476 erros (2026-10-26).

## TypeScript: `@welt-studio/tsconfig`

Pacote em `tsconfig/`, instalado por tag do git como o do ESLint:

```json
"@welt-studio/tsconfig": "github:welt-studio/standards#tsconfig-v1.0.1&path:/tsconfig"
```

```jsonc
// tsconfig.json do projeto: só fatos dele
{
  "extends": "@welt-studio/tsconfig/base.json",
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM"],
    "jsx": "react-jsx",
    "noEmit": true,
  },
  "include": ["src"],
}
```

A base liga, além do `strict`: `noUncheckedIndexedAccess` (acesso por índice pode ser `undefined`),
`noImplicitOverride`, `noImplicitReturns`, `noFallthroughCasesInSwitch`, `verbatimModuleSyntax`,
`isolatedModules` e `erasableSyntaxOnly` (sem `enum` nem parameter property). Variável e parâmetro
sem uso ficam com o ESLint. Módulo `ESNext` com resolução `bundler`, `skipLibCheck`.

O `tsc` checa o projeto inteiro (não há "só os arquivos do commit"): com a base adotada, a CI fica
vermelha até o projeto zerar os erros que ela acusa, que estão no índice de adequação dele.

## Prettier: `@welt-studio/prettier-config` e o hook `prettier-base`

Pacote em `prettier/`, instalado por tag do git como os outros, e declarado no `package.json` do
projeto, que não tem `.prettierrc`:

```json
"prettier": "@welt-studio/prettier-config",
"devDependencies": {
  "@welt-studio/prettier-config": "github:welt-studio/standards#prettier-v1.1.1&path:/prettier"
}
```

O estilo é o padrão do Prettier (aspas duplas, vírgula no fim em tudo, parênteses na arrow
function, `lf`), com `printWidth` 100. O plugin de GLSL vem no pacote: formata shader
(`.glsl`, `.vert`, `.frag`) e não faz nada em projeto sem shader. O `prettier` (3) é
`peerDependency`, na versão do projeto.

O `.prettierignore` fica só com o que é versionado e não se formata: os ignores comuns (saída de
gerador, `vendor/`, `*.min.*`; ver "Ignores comuns"), os lockfiles e os templates Jinja/Django. Ele não herda arquivo de pacote, então é cópia do
`prettier/ignore`, mantida pelo hook `prettier-base` (o mesmo `hooks/sync_base.py` do Ruff e do
Pyright).
Projeto em que o Prettier roda de dentro de uma pasta passa a pasta em `args`:

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/welt-studio/standards
  rev: prettier-v1.1.1
  hooks:
    - id: prettier-base
      args: [frontend] # só onde o Prettier roda de `frontend/`
```

O hook do Prettier é o mesmo em todo projeto: `pnpm exec prettier --write --ignore-unknown`, nos
arquivos do commit; na CI, o TS/JS fora do formato reprova pelo `prettier/prettier` do ESLint. O
projeto inteiro se formata pelo mesmo hook, nunca por `prettier .` direto:
`uvx pre-commit@4.7.0 run prettier --all-files`. O hook só recebe arquivo versionado e respeita o
`exclude` dele; o `prettier .` lê só o `.gitignore` da pasta de onde roda (não os de subpastas) e
entraria em `dist/`, artefatos e pastas ignoradas mais abaixo.

## jscpd: `jscpd/` pelo hook `jscpd-base`

O jscpd não herda config de pacote, então o padrão chega como cópia, pelo mesmo `hooks/sync_base.py`: o
hook `jscpd-base` mantém na raiz do projeto o `.jscpd.json` (a trava) e o `.jscpd-semantic.json` (o
relatório semântico). O JSON do jscpd não aceita comentário nem chave a mais (avisa campo
desconhecido a cada execução), então a cópia sai sem o aviso de "gerado, não edite": ele fica no
comentário do bloco do hook no `.pre-commit-config.yaml` do projeto, e o hook desfaz qualquer
edição da cópia.

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/welt-studio/standards
  rev: jscpd-v1.0.2
  hooks:
    - id: jscpd-base
```

| Arquivo                            | O que fixa                                                                                                                                                                                                                                                                                        |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.jscpd.json` (trava)              | Python, TS/TSX, JS/JSX e Rust, no repo inteiro; qualquer clone reprova (`exitCode` 1). Fora: o que o git ignora (o jscpd lê o `.gitignore`), migrations, `*.gen.ts`, `vendor/` e `*.min.*`. Linhas de import (TS/JS e Python) não contam: dois arquivos com os mesmos imports não duplicam lógica |
| `.jscpd-semantic.json` (relatório) | código que faz a mesma coisa escrito diferente, fora dos testes; não reprova. O projeto passa a pasta do relatório com `-o`                                                                                                                                                                       |

O hook da trava é o mesmo em todo projeto, sobre o repo inteiro (`pass_filenames: false`: a cópia
que importa é a de uma função que já existe em outro arquivo):
`pnpm exec jscpd .` na raiz, ou `bash -c 'cd frontend && pnpm exec jscpd -c ../.jscpd.json ..'` onde
o Node fica em `frontend/`. A versão do jscpd é a do lockfile do projeto. Os relatórios de código
morto e complexidade (`.jscpd-health.json`) são do projeto, porque os pontos de entrada são fatos
dele.

## pnpm: scripts de instalação das dependências

Nenhuma dependência roda script de instalação (`preinstall`/`install`/`postinstall`), e o projeto
só se instala pelo pnpm. São duas declarações, iguais em todo projeto, sem lista de pacotes:

```yaml
# pnpm-workspace.yaml
strictDepBuilds: false
```

```json
// package.json (a versão do pnpm fica só no `packageManager`)
"devEngines": {
  "packageManager": { "name": "pnpm", "onFail": "error" }
}
```

| Regra                                                          | Por quê                                                                                                                                                                                                                                                     |
| -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sem `allowBuilds`                                              | no pnpm, pacote fora do `allowBuilds` nunca roda script. Sem lista, nada roda, em nenhuma versão (um `true` liberaria também as versões futuras: o cenário do worm Shai-Hulud). Pacote que precise mesmo do script é exceção do PO, registrada no TECH_DEBT |
| `strictDepBuilds: false`                                       | com ele ligado (o padrão), cada pacote com script teria de ser listado à mão como `false` só para a instalação não travar, inclusive os de outro sistema (o `fsevents` do macOS). Desligado, a instalação passa e avisa: `Ignored build scripts: …`         |
| `devEngines.packageManager` com `onFail: "error"`              | `npm install` reprova (`EBADDEVENGINES`) sem instalar nada, então não há `.npmrc` a manter                                                                                                                                                                  |
| Sem `ignoreScripts` e sem `--ignore-scripts` no `pnpm install` | já não roda script nenhum; essas formas também pulam os scripts do próprio projeto e não avisam o que foi pulado                                                                                                                                            |

O hook `pnpm-base` (`hooks/check_pnpm.py`) trava a política: reprova o commit se faltar o
`strictDepBuilds: false` ou o `devEngines.packageManager`, ou se voltar `allowBuilds`,
`onlyBuiltDependencies`, `dangerouslyAllowAllBuilds` ou `ignoreScripts`. Use o pnpm do
`packageManager`: versões antigas do pnpm 12 reescrevem o `pnpm-workspace.yaml` a cada instalação
com um `allowBuilds` de placeholders, que o hook então acusa.

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/welt-studio/standards
  rev: pnpm-v1.0.0
  hooks:
    - id: pnpm-base
      args: [frontend] # só onde o pnpm-workspace.yaml não está na raiz
```

O `pnpm-lock.yaml` do pnpm 12 tem dois documentos YAML (o primeiro fixa o próprio pnpm, o segundo é
o lock), e o `check-yaml` recusa arquivo assim. A flag `--allow-multiple-documents` entra **só no
lockfile**, num hook próprio: valendo para todos os YAMLs, um `---` perdido num compose ou workflow,
que só lê o primeiro documento, passaria calado.

```yaml
# .pre-commit-config.yaml (repo pre-commit-hooks)
- id: check-yaml
  exclude: (^|/)pnpm-lock\.yaml$
- id: check-yaml
  name: Check YAML syntax (pnpm-lock, multi-documento)
  alias: check-yaml-pnpm-lock
  args: [--allow-multiple-documents]
  files: (^|/)pnpm-lock\.yaml$
```

## Testes (pytest): hook `pytest-base`

O pytest não tem `extends` e não mescla configs (vale o primeiro arquivo achado), então não há
cópia: o projeto é dono do `[tool.pytest.ini_options]` e do `[tool.coverage]`, e o hook
`pytest-base` (`hooks/check_pytest.py`) reprova, com o motivo, quando falta o que o padrão exige.

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/welt-studio/standards
  rev: pytest-v3.0.0
  hooks:
    - id: pytest-base
      args: [backend] # a pasta do pacote Python, quando o pyproject.toml não está na raiz
```

| Exigido                                                                                                                          | Por quê                                                                                                                |
| -------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `strict = true`                                                                                                                  | pytest 9: marker não declarado, opção de config desconhecida e `xfail` que passa viram erro                            |
| `filterwarnings` começando por `"error"`, e depois dele só a fronteira (abaixo); `addopts` sem `-W` nem `-p no:warnings`         | aviso do nosso código (depreciação, inclusive) reprova na hora; aviso que nasce dentro de lib não                      |
| `python_files = ["test_*.py"]`                                                                                                   | uma forma só de nome de arquivo de teste                                                                               |
| `addopts` com `--disable-socket` e `--allow-hosts=<hosts>`                                                                       | teste não acessa a rede; os hosts liberados (banco local) são fato do projeto                                          |
| `addopts` com `--cov` (ou `--cov=<pasta>`)                                                                                       | o `fail_under` só vale quando a cobertura roda: sem a flag no `addopts`, um `pytest` sem ela passa abaixo do piso      |
| `timeout = 60`                                                                                                                   | teste travado falha; o lento de propósito declara `@pytest.mark.timeout(...)`                                          |
| `[tool.coverage.run]` `branch = true`, `source`, sem `omit`                                                                      | a cobertura conta os dois lados de cada `if`, sobre todo o código da aplicação                                         |
| `[tool.coverage.report]` `fail_under = 80`                                                                                       | piso igual para todos (o do front é o mesmo)                                                                           |
| `[dependency-groups] dev` com `pytest-cov`, `pytest-xdist`, `pytest-randomly`, `pytest-timeout`, `pytest-socket`, `time-machine` | cobertura, paralelismo, ordem aleatória (pega teste que depende de outro), timeout, rede bloqueada, relógio controlado |

O filtro de avisos do Python vale para o processo inteiro: com só `"error"`, um aviso que nasce
dentro do diffusers ou do transformers reprova teste nosso, e a saída viraria corrigir lib de
terceiro. A régua é para o nosso código, então o projeto que depende de lib que avisa declara a
fronteira, inteira (com aspas simples: são regex, e o TOML não mexe na `\`):

```toml
filterwarnings = [
    'error',                               # exigido como primeira linha
    'default',                             # aviso emitido dentro de lib: relatório, não reprova
    'error::pytest.PytestWarning',         # aviso do pytest sobre os nossos testes
    'error::ResourceWarning',              # conexão ou arquivo que não foi fechado
    'error:::(.+\.)?(test_\w*|conftest)$', # módulos de teste e conftest, em qualquer modo de import
    'error:::nebulai(\.|$)',               # um por pacote do [tool.coverage.run] source
]
```

O pytest aplica a última regra que casar. O aviso é atribuído ao módulo que o `stacklevel` aponta:
quando o nosso código chama uma API depreciada da lib, o aviso cai na nossa linha e reprova, porque
a correção é nossa. Só o que nasce dentro da lib vira relatório.

- `pytest.PytestWarning`: classe de teste que não é coletada, exceção perdida numa thread ou no
  `__del__`, teste que devolve valor. O pytest emite esses avisos sem módulo nosso, então só a
  categoria os pega.
- `ResourceWarning`: o aviso de conexão ou arquivo não fechado sai quando o coletor destrói o
  objeto, e fica com o módulo que rodava naquela hora (até o `inspect` da stdlib), não com quem
  abriu. Por módulo, um vazamento nosso iria para o relatório.
- Testes: o nome do módulo muda com o modo de import (`test_x` no `prepend` sem `__init__.py`,
  `tests.test_x` no `importlib`); a regex casa pelo nome do arquivo, que o `python_files` fixa.
- Pacotes: o módulo é regex ancorada só no início, então o `(\.|$)` é obrigatório — sem ele,
  `error:::app` pegaria a lib `apprise`. Os pacotes saem do `[tool.coverage.run] source`, que com a
  fronteira lista nomes de import (`app`, `app/core` vira `app\.core`; `.` não serve).

Depois do `"error"`, o hook aceita só isso: nada, ou essa fronteira, completa e com os pacotes do
`source` (a ordem depois do `default` é livre). Na falta, ele imprime a lista certa para colar.
Exceção por lib ou por mensagem (`ignore::DeprecationWarning:diffusers`, `ignore`) reprova, e
também `-W`/`--pythonwarnings` e `-p no:warnings` no `addopts`, que valem por cima do ini: com a
fronteira nenhuma exceção é necessária. Fica fora do alcance do hook, que só lê o `pyproject.toml`,
o `@pytest.mark.filterwarnings("ignore…")` num teste.

Fica com o projeto o que é fato dele: `testpaths`, `pythonpath`, markers, `asyncio_mode`,
`DJANGO_SETTINGS_MODULE`, o número de workers do xdist. Com o `--cov` no `addopts`, a CI e o
`pre-push` rodam só `uv run pytest` (o `--cov-report=term-missing:skip-covered` no `addopts` mostra
as linhas que faltam).

Rodar um arquivo ou um teste só: `uv run pytest --no-cov <caminho>`. Com o `--cov` no `addopts`, a
cobertura é medida em toda execução, e um teste isolado cobre pouco do código: sem o `--no-cov`, o
pytest termina com "Required test coverage of 80% not reached" e sai com falha, mesmo com todos os
testes passando. O piso vale para a suíte inteira (CI e `pre-push`). O mesmo no vitest: `vitest run
<arquivo>`, sem `--coverage`.

O hook reprova também `pyproject.toml` que não é TOML válido, com o erro do
parser. Os testes do hook ficam em `tests/test_check_pytest.py` (ver "Desenvolver este repo").

## Dependências Python (deptry): hook `deptry`

O [deptry](https://deptry.com/) compara os imports do código com as dependências do
`pyproject.toml` do pacote, como o Knip faz no JS com o `package.json`. O hook `deptry` roda
`uv run --directory <pacote> deptry .` e reprova com o que ele acusa:

| Regra    | O que reprova                                                                                                         |
| -------- | --------------------------------------------------------------------------------------------------------------------- |
| `DEP001` | import de pacote que não está declarado (funciona só porque veio como dependência de outro, ou porque sobrou no venv) |
| `DEP002` | dependência declarada que nenhum código importa                                                                       |
| `DEP003` | import direto de dependência transitiva: declarada por outro pacote, não pelo projeto                                 |
| `DEP004` | dependência do grupo `dev` importada no código da aplicação (no deploy, sem o `dev`, o import quebra)                 |

O projeto adota com o deptry no grupo `dev` (`uv add --dev deptry`; a versão é a do `uv.lock`, que
o Renovate sobe) e o hook:

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/welt-studio/standards
  rev: deptry-v1.0.0
  hooks:
    - id: deptry
      args: [backend] # a pasta do pacote Python (obrigatória; `.` quando o pyproject.toml é o da raiz)
```

O hook não tem script: ele chama o `uv` direto (`language: system`). Sem o `deptry` no grupo `dev`,
o uv reprova com `Failed to spawn: deptry`. O deptry roda no ambiente do projeto (`uv run`), e não
num ambiente isolado do pre-commit, porque é pelos metadados dos pacotes instalados que ele sabe de
que distribuição vem cada import (`yaml` → `pyyaml`). Ele
roda quando o commit toca `.py`, `pyproject.toml` ou `uv.lock`, sobre o pacote inteiro
(`pass_filenames: false`): a dependência que sobra é a que o commit deixou de importar.

Exceção vai no `[tool.deptry.per_rule_ignores]` do `pyproject.toml` do pacote, só para fato do
projeto, com o motivo num comentário: pacote que nenhum código importa porque é usado por CLI, entry
point, driver ou plugin carregado por string (o `psycopg` que o Django carrega pelo `ENGINE`, o
`uvicorn` do comando de subida). O deptry reconhece como código próprio só o que está na raiz do
pacote; módulo em outra pasta (layout `src/`, ou scripts importados pelo nome, como os de `hooks/`
deste repo) vai no `known_first_party` do `[tool.deptry]`, o mesmo fato do `known-first-party` do
Ruff.

```toml
[tool.deptry.per_rule_ignores]
# O Django carrega o driver do banco pelo `ENGINE` do settings, por string.
DEP002 = ["psycopg"]
```

## Testes (vitest): `@welt-studio/vitest-config`

Pacote em `vitest/`, instalado por tag do git como os outros. O projeto só declara os aliases (e um
setup próprio, se tiver):

```typescript
// vitest.config.ts
import { weltVitestConfig } from "@welt-studio/vitest-config";
import { mergeConfig } from "vitest/config";

import viteConfig from "./vite.config";

export default mergeConfig(weltVitestConfig(), { resolve: viteConfig.resolve });
```

| O que fixa                                               | Por quê                                                                                                                                                                                                                                                                                                              |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `jsdom`, `--no-webstorage`                               | o `localStorage` do Node 25+ cobriria o do jsdom                                                                                                                                                                                                                                                                     |
| `globals: false`                                         | `describe`/`it`/`expect` importados de `"vitest"`: sem import, o `tsc` reprova                                                                                                                                                                                                                                       |
| `include: ["src/**/*.test.{ts,tsx}"]`                    | teste unitário ao lado do arquivo que testa; E2E é do Playwright                                                                                                                                                                                                                                                     |
| `sequence.shuffle`                                       | ordem aleatória                                                                                                                                                                                                                                                                                                      |
| `restoreMocks`                                           | todo `vi.spyOn` volta ao original depois de cada teste: mock esquecido não vaza para o teste seguinte                                                                                                                                                                                                                |
| Cobertura v8 sobre `src/**`, piso 80 nas quatro métricas | o mesmo piso do backend, contando o código que nenhum teste importa                                                                                                                                                                                                                                                  |
| Setup                                                    | `jest-dom`, `cleanup()` entre testes (sem `globals` o Testing Library não limpa sozinho) e o servidor MSW com `onUnhandledFrame: "error"`: requisição sem handler reprova, nada sai para a rede. O projeto registra os handlers com `server.use(...)` (`import { server } from "@welt-studio/vitest-config/server"`) |

O jsdom vem do pacote. O projeto instala o `vitest` e o `@vitest/coverage-v8`, **na mesma versão**:
o `coverage-v8` exige a versão exata do `vitest` como `peerDependency`, e o Vitest avisa "Running
mixed versions is not supported" quando elas diferem (o Renovate sobe as duas no mesmo PR, pelo
grupo de monorepo do Vitest que o `config:recommended` traz). O que o teste importa (`@testing-library/react`, `@testing-library/dom`,
`@testing-library/jest-dom`, `msw`) o projeto também declara, porque o pnpm só deixa importar o que
está no `package.json` (e o Knip cobra o mesmo); os `peerDependencies` do pacote dizem as versões
aceitas, com a mesma faixa para o `vitest` e o `coverage-v8` (o teste do pacote confere). Projeto sem nenhum teste reprova na CI (`vitest run` sem arquivo
de teste sai com erro). Scripts: `test` (`vitest run`) e `test:coverage` (`vitest run --coverage`),
este na CI.
