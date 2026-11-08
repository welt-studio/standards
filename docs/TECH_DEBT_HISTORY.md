# Débitos Técnicos — Histórico

## Arquitetura / Design

### [Renovate] Regras de regex que existem só por causa do comichub e do nebulai

- [x] **Severidade**: Baixa · `2026-10-28`
- **Arquivos**: `renovate/default.json5`
- **Descrição**: dois `customManagers` do preset, que vale para todos os projetos, carregam padrão
  que só um projeto usa. No de uv, o `managerFilePatterns` `"/(^|/)scripts/[^/]+\\.m?js$/"` e o
  `matchStrings` `UV_VERSION\s*=\s*"…"` existem só pela constante do instalador do nebulai, que
  repete a versão do uv em vez de ler o `[tool.uv] required-version`. No de pnpm, o `matchStrings`
  `ARG PNPM_VERSION=…` existe só pelo Dockerfile do comichub, que declara a versão num `ARG` em
  vez do `FROM ghcr.io/pnpm/pnpm:<versão>` direto dos outros. Enquanto isso, o preset varre
  `scripts/*.mjs` de todo projeto e aceita `ARG PNPM_VERSION` como forma válida. No
  `eslint/index.mjs` e no `eslint/i18n.mjs` não há regra exclusiva de projeto: as listas de
  atributos e chamadas do i18n são genéricas (o comentário do pg-studio no `commonIgnores` só conta
  o caso que motivou o `**/`).
- **Sugestão**: corrigir nos projetos (débitos já registrados no TECH_DEBT de cada um): o
  instalador do nebulai lê o `required-version`, e o Dockerfile do comichub usa o `FROM` direto.
  Feito isso, sai do preset o terceiro padrão de arquivo e o terceiro `matchStrings` do uv, e o
  segundo `matchStrings` do pnpm.
- **Resolvido**: `2026-11-08` — o comichub passou a usar o `FROM ghcr.io/pnpm/pnpm:<versão>`
  direto, e o nebulai não tem mais o `UV_VERSION` no instalador. Saíram do preset o padrão
  `scripts/*.mjs` e os `matchStrings` do `UV_VERSION` e do `ARG PNPM_VERSION`.

### [uv] Versão do uv declarada duas vezes nos projetos (imagem Docker e `required-version`)

- [x] **Severidade**: Baixa · `2026-11-07`
- **Arquivos**: nos projetos, o Dockerfile (`ghcr.io/astral-sh/uv:<versão>`) e o `pyproject.toml`
  (`[tool.uv] required-version`)
- **Descrição**: o `COPY --from=` e o `FROM` não leem o `pyproject.toml`, então a versão do uv
  aparece nos dois lugares. O Renovate sobe os dois no mesmo PR (o regex do preset e o
  `group:allNonMajor`), mas nada reprova a divergência que alguém escrever à mão. Esta é a segunda
  metade do item 3 do comichub, que ficou fora do `python-base` e sem decisão.
- **Sugestão**: decisão do PO entre (a) uma checagem no `python-base` ou num hook próprio que
  compare a tag da imagem com o `required-version` e (b) aceitar as duas declarações, já que o
  Renovate as sobe juntas.
- **Resolvido**: `2026-11-08` — opção (a), decisão do PO: o `python-base` (`python-v1.1.0`) reprova a
  tag da imagem do uv que divergir do `required-version`, e o `pnpm-base` (`pnpm-v1.1.0`) faz o
  mesmo com a tag da imagem do pnpm contra o `packageManager`, que antes só o comichub conferia (no
  `frontend.yml`).

### [Pyright] Hook `pyright-django` para os stubs do Django

- [x] **Severidade**: Baixa · `2026-10-27`
- **Descrição**: proposta de pôr no standards um hook opt-in com a configuração de Pyright para
  projeto Django (stubs `django-types`/`djangorestframework-stubs`), depois da comparação
  Pyright × Pyrefly × mypy, em que o padrão ficou no Pyright.
- **Sugestão**: hook `pyright-django` no `.pre-commit-hooks.yaml`, usado só por projeto Django.
- **Resolvido**: `2026-10-30` — Descartado (decisão do PO): o comichub, único projeto Django,
  resolveu os stubs no próprio projeto, e um hook que só um projeto usa vai contra o padrão único.
  Volta a valer se um segundo projeto Django entrar.
