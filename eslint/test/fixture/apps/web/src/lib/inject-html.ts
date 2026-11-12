// Caso: HTML montado a partir de texto chega ao DOM sem sanitizar (XSS). Reprova o
// `no-unsanitized/property` (`innerHTML`) e o `no-unsanitized/method` (`insertAdjacentHTML`); o
// `textContent` não interpreta HTML e passa.
export function render(target: HTMLElement, name: string): void {
  target.innerHTML = `<p>${name}</p>`;
  target.insertAdjacentHTML("beforeend", name);
  target.textContent = name;
}
