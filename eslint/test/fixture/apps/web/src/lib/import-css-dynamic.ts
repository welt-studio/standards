// `import()` de CSS fora do `main.tsx`: reprova, como o import estático.
export const loadTheme = () => import("./theme.css");
