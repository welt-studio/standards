export function handler(req) {
  let p = path.normalize(req.query.p);
  if (!path.isAbsolute(p) && !p.startsWith("..")) {
    fs.readFileSync(p);
  }
  p = decodeURIComponent(p);
  if (!path.isAbsolute(p) && !p.startsWith("..")) {
    fs.readFileSync(p);
  }
}
