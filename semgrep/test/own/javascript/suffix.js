// own-test: js/incorrect-suffix-check
// Verificação de sufixo com indexOf (js/incorrect-suffix-check), conferida contra o
// IncorrectSuffixCheck.ql do CodeQL: o comprimento subtraído é o do mesmo receptor e do mesmo
// argumento da chamada, e as verificações de -1 e de `>= 0` valem para a mesma chamada.

function operators(value, suffix) {
  const a = value.indexOf(suffix) === value.length - suffix.length; // $ Alert[js/incorrect-suffix-check]
  const b = value.indexOf(suffix) == value.length - suffix.length; // $ Alert[js/incorrect-suffix-check]
  const c = value.indexOf(suffix) !== value.length - suffix.length; // $ Alert[js/incorrect-suffix-check]
  const d = value.indexOf(suffix) != value.length - suffix.length; // $ Alert[js/incorrect-suffix-check]
  // A ordem dos operandos não importa (`EqualityTest.hasOperands`).
  const e = value.length - suffix.length === value.indexOf(suffix); // $ Alert[js/incorrect-suffix-check]
  const f = value.lastIndexOf(suffix) === value.length - suffix.length; // $ Alert[js/incorrect-suffix-check]
  return [a, b, c, d, e, f];
}

function variables(value, suffix) {
  const index = value.indexOf(suffix);
  const delta = value.length - suffix.length;
  const a = index !== delta; // $ Alert[js/incorrect-suffix-check]
  const b = index === value.length - suffix.length - 1; // $ Alert[js/incorrect-suffix-check]
  const c = delta === index; // $ Alert[js/incorrect-suffix-check]
  const d = value.indexOf(suffix) === delta; // $ Alert[js/incorrect-suffix-check]
  return [a, b, c, d];
}

function unrelated(value, suffix, other, total, size) {
  // O comprimento tem de ser o do mesmo receptor e do mesmo argumento.
  const a = value.indexOf(suffix) === other.length - suffix.length;
  const b = value.indexOf(suffix) === value.length - other.length;
  const c = value.indexOf(suffix) === total;
  const index = value.indexOf(suffix);
  const d = index === size;
  const e = index === total - 1;
  const delta = other.length - suffix.length;
  const f = value.indexOf(suffix) === delta;
  return [a, b, c, d, e, f];
}

function oneCharacter(path) {
  // Um literal de um caractere só falha com a string vazia: o CodeQL ignora.
  const a = path.indexOf("/") === path.length - 1;
  const b = path.lastIndexOf(".") === path.length - 1;
  const sep = "/";
  const c = path.indexOf(sep) === path.length - sep.length; // $ Alert[js/incorrect-suffix-check]
  return [a, b, c];
}

function literals(host, name) {
  // O número é o comprimento do literal (`lengthExpr.getIntValue() = val.length()`).
  const a = host.indexOf(".example.com") === host.length - 12; // $ Alert[js/incorrect-suffix-check]
  const b = name.lastIndexOf(".png") === name.length - 4; // $ Alert[js/incorrect-suffix-check]
  const c = name.indexOf(".png") === name.length - 5;
  const d = name.indexOf(".png") === name.length - 3;
  const e = name.indexOf(".png") === name.length - 1;
  // Só vale a verificação de comprimento do próprio literal; o 5 da outra linha não é dele.
  const f = host.length >= 5 && host.indexOf(".example.com") === host.length - 12; // $ Alert[js/incorrect-suffix-check]
  const g = host.length >= 12 && host.indexOf(".example.com") === host.length - 12;
  return [a, b, c, d, e, f, g];
}

function guards(value, suffix, other) {
  // Comparar os comprimentos, ou testar o -1 da mesma chamada, resolve.
  const a = value.length >= suffix.length && value.indexOf(suffix) === value.length - suffix.length;
  const b = value.indexOf(suffix) !== -1 && value.indexOf(suffix) === value.length - suffix.length;
  const c = value.indexOf(suffix) > -1 && value.indexOf(suffix) === value.length - suffix.length;
  const index = value.lastIndexOf(suffix);
  const d = index !== -1 && index === value.length - suffix.length;
  const e = index >= 0 && index === value.length - suffix.length;
  // Verificar outra chamada, outro argumento ou outro método não resolve.
  const f = value.indexOf(other) !== -1 && value.indexOf(suffix) === value.length - suffix.length; // $ Alert[js/incorrect-suffix-check]
  const g = other.indexOf(suffix) !== -1 && value.indexOf(suffix) === value.length - suffix.length; // $ Alert[js/incorrect-suffix-check]
  const h = value.lastIndexOf(suffix) !== -1 && value.indexOf(suffix) === value.length - suffix.length; // $ Alert[js/incorrect-suffix-check]
  const i = other !== -1 && index === value.length - suffix.length; // $ Alert[js/incorrect-suffix-check]
  const j = index !== 0 && index === value.length - suffix.length; // $ Alert[js/incorrect-suffix-check]
  // Um limite que não é de comprimento não resolve.
  const k = value.length >= 4 && value.indexOf(suffix) === value.length - suffix.length; // $ Alert[js/incorrect-suffix-check]
  return [a, b, c, d, e, f, g, h, i, j, k];
}
