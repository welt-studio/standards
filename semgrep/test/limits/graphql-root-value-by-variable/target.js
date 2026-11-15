const { graphql } = require("graphql");

// Controle: o objeto escrito dentro da chamada recebe o dado (a linha do eval é achada).
function inline(req, schema) {
  graphql({
    schema,
    rootValue: { calc: (args) => eval(args.expr) },
    variableValues: req.body.variables,
  });
}

function filler() {
  return 1;
}

function filler2() {
  return 2;
}

// O objeto é definido antes e passado por variável: o parâmetro da função dele não recebe o dado.
function byVariable(req, schema) {
  const root = { calc: (args) => eval(args.expr) };
  graphql({ schema, rootValue: root, variableValues: req.body.variables });
}
