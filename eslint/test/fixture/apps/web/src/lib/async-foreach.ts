// Caso: função async onde se espera `void`, fora do JSX, continua reprovando no
// `no-misused-promises`.
export function each(values: number[]): void {
  values.forEach(async (value) => {
    await Promise.resolve(value);
  });
}
