// own-test: js/sql-injection
// Banco do pg-promise declarado pelo tipo (js/sql-injection), com a revisão de 2026-11-14 contra o
// SQL.qll do CodeQL (`API::Node::ofType("pg-promise", "IBaseProtocol")`).
import { IDatabase } from "pg-promise";
import express from "express";

const app = express();

interface Rows {
  one(text: string): string;
}

class Accounts {
  db: IDatabase<unknown>;
  rows: Rows;

  find(id: string): void {
    // O campo tem o tipo do pg-promise; o outro, com o mesmo método, não.
    this.db.one("select * from accounts where id = " + id); // $ Alert[js/sql-injection]
    this.rows.one("select * from accounts where id = " + id);
  }
}

// A requisição vem de uma rota registrada; o que o caso testa é o tipo do banco.
app.get("/accounts", (req, res) => res.json(new Accounts().find(req.query.id)));
