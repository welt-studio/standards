// Controle: a lista escrita de uma vez e a montada por push reúnem os dois rótulos.
function literal() {
  const args = [sourceFlag(), sourceUser()];
  sink(args);
}

function filler() {
  return 1;
}

function pushes() {
  const args = [];
  args.push(sourceFlag());
  args.push(sourceUser());
  sink(args);
}

function filler2() {
  return 2;
}

// A lista montada por atribuição de índices não reúne os dois rótulos.
function indexWrites() {
  const args = [];
  args[0] = sourceFlag();
  args[1] = sourceUser();
  sink(args);
}
