const mongoose = require("mongoose");

function handler(req, Model) {
  const query = req.body;
  if (mongoose.Types.ObjectId.isValid(query)) {
    Model.find(query);
  } else {
    Model.find(query);
  }
}
