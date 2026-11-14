const fastify = require("fastify")();

fastify.addHook("preHandler", async (request) => {
  request.stored = request.query.code;
});
fastify.get("/run", async (request) => {
  return eval(request.stored);
});
