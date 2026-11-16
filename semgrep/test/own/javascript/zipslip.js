// own-test: js/zipslip
// Zip Slip (js/zipslip), conferido contra o ZipSlipCustomizations.qll e o Files.qll do CodeQL: as
// fontes são o caminho da entrada de uma instância de jszip, adm-zip, unzipper/unzip ou tar-stream
// (pelo módulo importado), e os sumidouros só os de escrita (`FileSystemWriteAccess`).
const fs = require("fs");
const path = require("path");
const JSZip = require("jszip");
const AdmZip = require("adm-zip");
const unzipper = require("unzipper");
const tar = require("tar-stream");
const { EventEmitter } = require("events");
const { Writer } = require("fstream");
const otherArchive = require("other-archive");

const bundle = new JSZip();
const outputDir = path.resolve("/srv/output");

function jszipFiles(libs, reader) {
  // O `forEach` e o `filter` de uma instância de jszip entregam o caminho relativo da entrada.
  bundle.forEach((relativePath) => {
    fs.writeFileSync(relativePath, "x"); // $ Alert[js/zipslip]
  });
  bundle.filter(function (relativePath) {
    fs.appendFile(relativePath, "x", () => {}); // $ Alert[js/zipslip]
    return true;
  });
  for (const entryName in bundle.files) {
    fs.createWriteStream(entryName); // $ Alert[js/zipslip]
  }
  // Qualquer outro objeto com `forEach` não é um arquivo compactado.
  libs.forEach((lib) => {
    fs.writeFileSync(lib, "x");
  });
  reader.files.forEach((item) => {
    fs.writeFileSync(item, "x");
  });
  for (const key in reader.files) {
    fs.writeFileSync(key, "x");
  }
}

function jszipSinks() {
  // Só a escrita (`FileSystemWriteAccess`): o `open` em modo de escrita e o `link` (os dois
  // argumentos) são sumidouro; a leitura, a consulta e o `open` de leitura não são.
  bundle.forEach((relativePath) => {
    fs.openSync(relativePath, "w"); // $ Alert[js/zipslip]
    fs.link(relativePath, "/srv/copy", () => {}); // $ Alert[js/zipslip]
    fs.linkSync("/srv/original", relativePath); // $ Alert[js/zipslip]
    fs.openSync(relativePath, "r");
    fs.readFileSync(relativePath);
    fs.statSync(relativePath);
    fs.existsSync(relativePath);
    fs.readdirSync(relativePath);
  });
}

function unzipperEntries(source) {
  source.pipe(unzipper.Parse()).on("entry", (entry) => {
    const target = entry.path;
    fs.writeFile(target, "x", () => {}); // $ Alert[js/zipslip]
  });
  const parser = unzipper.Parse();
  parser.on("entry", function (item) {
    fs.createWriteStream(item.path); // $ Alert[js/zipslip]
  });
  // Outro emissor com o evento `entry`, ou outro módulo com `Parse`, não é arquivo compactado.
  const emitter = new EventEmitter();
  emitter.on("entry", (item) => {
    fs.createWriteStream(item.path);
  });
  source.pipe(otherArchive.Parse()).on("entry", (item) => {
    fs.createWriteStream(item.path);
  });
  // O CodeQL só lê `path`, `name` e `linkname`.
  source.pipe(unzipper.Parse()).on("entry", (item) => {
    fs.createWriteStream(item.fileName);
    fs.createWriteStream(item.header.name);
    fs.createWriteStream(item.type);
  });
}

function tarEntries(source) {
  const extract = tar.extract();
  extract.on("entry", (header, stream, next) => {
    fs.createWriteStream(header.name); // $ Alert[js/zipslip]
    fs.linkSync(header.linkname, "/srv/target"); // $ Alert[js/zipslip]
    next();
  });
  source.pipe(tar.extract()).on("entry", (header) => {
    fs.createWriteStream(header.name); // $ Alert[js/zipslip]
  });
  // O `filter` da extração do pacote `tar` não é fonte.
  tar.extract({
    filter: (item) => {
      fs.createWriteStream(item.path);
      return true;
    },
  });
}

function admZipEntries(archivePath) {
  const archive = new AdmZip(archivePath);
  const first = archive.getEntry("a.txt");
  fs.writeFileSync(first.entryName, "x"); // $ Alert[js/zipslip]
  fs.writeFileSync(archive.getEntry("b.txt").entryName, "x"); // $ Alert[js/zipslip]
  const entries = archive.getEntries();
  entries.forEach((item) => {
    fs.writeFileSync(item.entryName, "x"); // $ Alert[js/zipslip]
  });
  archive.getEntries().map(function (item) {
    return fs.createWriteStream(item.entryName); // $ Alert[js/zipslip]
  });
  fs.writeFileSync(entries[0].entryName, "x"); // $ Alert[js/zipslip]
  // A lista de entradas em si não é um caminho, e um objeto que só se parece com o adm-zip não conta.
  fs.writeFileSync(archive.getEntries(), "x");
  const fake = makeArchive();
  fake.getEntry("a.txt").entryName;
  fs.writeFileSync(fake.getEntry("a.txt").entryName, "x");
  fake.getEntries().forEach((item) => {
    fs.writeFileSync(item.entryName, "x");
  });
}

function fstreamWriter(source) {
  bundle.forEach((relativePath) => {
    source.pipe(Writer({ path: relativePath })); // $ Alert[js/zipslip]
  });
  // `Writer` que não vem do fstream não grava.
  const Other = otherArchive.Writer;
  bundle.forEach((relativePath) => {
    source.pipe(Other({ path: relativePath }));
  });
}

function guards() {
  bundle.forEach((relativePath) => {
    const target = path.resolve(outputDir, relativePath);
    if (!target.startsWith(outputDir)) {
      throw new Error("fora do diretório");
    }
    // A guarda limpa só o `target` que ela conferiu, não o `relativePath` de onde ele veio.
    fs.writeFileSync(target, "x");
    fs.writeFileSync(relativePath, "x"); // $ Alert[js/zipslip]
  });
  bundle.forEach((relativePath) => {
    const target = path.resolve(outputDir, relativePath);
    if (target.startsWith(outputDir)) {
      fs.writeFileSync(target, "x");
      fs.writeFileSync(relativePath, "x"); // $ Alert[js/zipslip]
    }
  });
}
