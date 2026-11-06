// Caso: em teste, `expect(fake.metodo)` passa no `unbound-method` (a versão do vitest) e um teste
// que verifica por helper `expect*` passa no `expect-expect`.
import { expect, it } from "vitest";

class Fake {
  readonly calls: number[] = [];

  save(value: number): void {
    this.calls.push(value);
  }
}

function expectSaved(fake: Fake, value: number): void {
  expect(fake.calls).toContain(value);
}

it("salva", () => {
  const fake = new Fake();
  fake.save(1);
  expect(fake.save).toBeDefined();
  expectSaved(fake, 1);
});
