// O CSS do jeito do padrão passa: o de pacote antes, e o `./index.css` por último.
import "@fontsource/inter/400.css";
import "./index.css";

import { app } from "@/app/app";

export const main = app;
