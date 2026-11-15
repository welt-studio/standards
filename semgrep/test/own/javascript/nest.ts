// own-test: js/command-line-injection
// NestJS (Nest.qll do CodeQL, revisão de 2026-11-14): só o parâmetro com `@Query`, `@Param`,
// `@Headers`, `@Body`... de um método com `@Get`, `@Post`... é fonte, e some quando um pipe converte
// o valor. `@Req` e `@Request` dão o objeto do Express: só as leituras dele são fonte.
import { Controller, Get, Post, Body, Query, Param, Req, ParseIntPipe } from "@nestjs/common";
import * as cp from "child_process";
import { Request } from "express";

@Controller("posts")
export class PostsController {
  @Get(":id")
  find(@Param("id") id: string, @Query() query: any, @Param("n", ParseIntPipe) n: number) {
    cp.exec(id); // $ Alert[js/command-line-injection]
    cp.exec(query.cmd); // $ Alert[js/command-line-injection]
    // `ParseIntPipe` converte o valor: o parâmetro não é fonte.
    cp.exec(n);
  }

  @Post()
  create(@Body() body: any, @Req() req: Request) {
    cp.exec(body.cmd); // $ Alert[js/command-line-injection]
    cp.exec(req.query.cmd); // $ Alert[js/command-line-injection]
    // O objeto inteiro da requisição não é fonte, só as leituras dele.
    cp.exec(req);
  }

  // Sem `@Get`, `@Post`... o método não é tratador de rota.
  helper(@Body() other: any) {
    cp.exec(other);
  }
}

// `@Body` de uma biblioteca que não é o `@nestjs/common` não é do Nest.
function Cookies() {
  return (target: unknown, key: string, index: number) => undefined;
}

export class Other {
  read(@Cookies() cookie: string) {
    cp.exec(cookie);
  }
}
