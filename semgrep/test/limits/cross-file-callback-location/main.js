import * as lib from "./lib";

const policy = trustedTypes.createPolicy("x", { createHTML: lib.createHtml });
policy.createHTML(window.name);
