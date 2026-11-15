// own-test: js/xss
// Biblioteca `history` (js/xss): só o histórico do navegador (`createBrowserHistory`) é sumidouro de
// URL; o `createHashHistory` só mexe no fragmento (History.qll e ClientSideUrlRedirectCustomizations.qll).
import { createBrowserHistory, createHashHistory } from "history";

const browserHistory = createBrowserHistory();
const hashHistory = createHashHistory();

browserHistory.push(window.name); // $ Alert[js/xss]
browserHistory.replace(window.name); // $ Alert[js/xss]
hashHistory.push(window.name);
hashHistory.replace(window.name);
