const mongoose = require("mongoose");

function handler(req) {
  const query = {};
  query.title = req.body.title;
  function getQueryConstructor() {
    return mongoose.Query;
  }
  const Q = getQueryConstructor();
  new Q(1, 2, query);
}
