# Testes do CodeQL

Cópia dos testes do [github/codeql](https://github.com/github/codeql), sob a licença MIT
(`LICENSE`). Vêm só as pastas de teste das consultas que as regras de `semgrep/` portam, sem
mudança: código de terceiros, fora do lint e dos hooks que reformatam.

- `SOURCE`: o commit do CodeQL de onde as pastas vieram (a única declaração dele).
- `queries.json`: que consultas cada pasta testa (gerado).
- `<linguagem>/<pasta>/`: a pasta de teste, com o `.expected` que diz onde o CodeQL acusa.

Não edite à mão. Para trocar de commit: subir o `SOURCE`, pôr um clone do CodeQL nesse commit e
rodar `uv run python hooks/sync_codeql_tests.py <clone>`.
