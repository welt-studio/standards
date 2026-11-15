const hb = require("handlebars");
const fs = require("fs");

hb.registerHelper("catFile", function catFile(filePath) {
  return fs.readFileSync(filePath);
});
const compiled = hb.compile("contents: {{catFile path}}");

app.get("/some/path", function (req, res) {
  res.send(compiled({ path: req.params.path }));
});

// Controle: a chamada direta do mesmo dado ao `fs` é achada.
app.get("/direct", function (req, res) {
  res.send(fs.readFileSync(req.params.path));
});
