export function handler(req) {
  const path = req.query.path;
  const obj = bla ? something() : path;
  obj.sub = "safe";
  fs.readFileSync(obj.sub);
  if (random()) {
    obj.other = "safe";
  }
  fs.readFileSync(obj.other);
}
