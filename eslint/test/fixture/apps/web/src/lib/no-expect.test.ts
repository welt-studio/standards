// Caso: teste sem `expect` nem helper `expect*` continua reprovando no `vitest/expect-expect`.
import { it } from "vitest";

function checkEven(value: number): boolean {
  return value % 2 === 0;
}

it("par", () => {
  checkEven(2);
});
