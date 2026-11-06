// Caso: em teste, método solto fora do `expect` continua reprovando no `vitest/unbound-method`.
import { expect, it } from "vitest";

class Store {
  readonly items: number[] = [];

  add(value: number): void {
    this.items.push(value);
  }
}

it("adiciona", () => {
  const store = new Store();
  const add = store.add;
  expect(add).toBeDefined();
});
