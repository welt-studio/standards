const fastify = require("fastify")();

fastify.get("/run", async (request) => {
  request.stored = request.query.code;
  return eval(request.stored);
});
