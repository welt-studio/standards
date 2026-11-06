// Caso: arrow de uma linha que chama função `void`, onde se espera `void`, passa no
// `no-confusing-void-expression`.
const values: number[] = [];

function push(value: number): void {
  values.push(value);
}

export const add: (value: number) => void = (value) => push(value);
