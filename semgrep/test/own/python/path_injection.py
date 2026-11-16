# own-test: py/path-injection
# Injeção de caminho (py/path-injection), conferida contra o Stdlib.qll, Flask.qll, Werkzeug.qll,
# Starlette.qll, FastApi.qll e PathInjectionQuery.qll do CodeQL.
import os
import pathlib
import shutil
import uuid
from pathlib import Path

from django.contrib.auth.decorators import login_required
from fastapi import FastAPI
from fastapi.responses import FileResponse as FastFileResponse
from flask import Flask, abort, request, send_file, send_from_directory
from pydantic import BaseModel
from starlette.responses import FileResponse as StarFileResponse
from werkzeug.utils import secure_filename

app = Flask(__name__)
api = FastAPI()
ROOT = "/srv/files"


@app.route("/conversion")
def conversion():
    name = request.args["name"]
    # O sumidouro de dentro da conversão continua alertando (`exact`): só o valor convertido é limpo.
    int(os.path.getmtime(name))  # $ Alert[py/path-injection]
    str(uuid.UUID(os.path.getsize(name)))  # $ Alert[py/path-injection]
    os.path.getmtime(int(name))
    safe = int(name)
    os.remove(str(safe))
    return "ok"


@app.route("/flask-send")
def flask_send():
    name = request.args["name"]
    folder = request.args["folder"]
    # Só o diretório é sumidouro: o Flask confina o nome do arquivo dentro dele.
    send_from_directory(ROOT, name)
    send_from_directory(folder, "index.html")  # $ Alert[py/path-injection]
    send_file(name)  # $ Alert[py/path-injection]
    return "ok"


@app.route("/normalize")
def normalize():
    name = request.args["name"]
    # realpath só normaliza, não acessa o disco: não é sumidouro.
    resolved = os.path.realpath(ROOT + "/" + name)
    if not resolved.startswith(ROOT):
        abort(404)
    return open(resolved).read()


@app.route("/normalize-bad")
def normalize_bad():
    name = request.args["name"]
    # A conferência do prefixo sem a normalização antes não vale (estado NotNormalized).
    if not name.startswith(ROOT):
        abort(404)
    return open(name).read()  # $ Alert[py/path-injection]


@app.route("/normalize-positive")
def normalize_positive():
    name = request.args["name"]
    full = os.path.normpath(ROOT + "/" + name)
    if full.startswith(ROOT):
        return open(full).read()
    return "no"


@app.route("/normalize-return")
def normalize_return():
    name = request.args["name"]
    full = os.path.abspath(ROOT + "/" + name)
    if not full.startswith(ROOT):
        return "no"
    return open(full).read()


@app.route("/normalize-raise")
def normalize_raise():
    name = request.args["name"]
    full = os.path.abspath(ROOT + "/" + name)
    if not full.startswith(ROOT):
        raise ValueError("fora")
    return open(full).read()


@app.route("/normalize-no-exit")
def normalize_no_exit():
    name = request.args["name"]
    full = os.path.abspath(ROOT + "/" + name)
    if not full.startswith(ROOT):
        print("fora")
    return open(full).read()  # $ Alert[py/path-injection]


@app.route("/relative")
def relative():
    name = request.args["name"]
    full = Path(ROOT) / name
    if not full.is_relative_to(ROOT):
        abort(404)
    return full.read_text()


@app.route("/relative-no-exit")
def relative_no_exit():
    name = request.args["name"]
    full = Path(ROOT) / name
    if not full.is_relative_to(ROOT):
        print("fora")
    return full.read_text()  # $ Alert[py/path-injection]


@app.route("/relative-and")
def relative_and():
    name = request.args["name"]
    full = Path(ROOT) / name
    if full.is_relative_to(ROOT) and full.exists():
        return full.read_text()
    return "no"


@app.route("/filenames")
def filenames():
    name = request.args["name"]
    # Divergência declarada: o CodeQL propaga a contaminação por estas funções.
    with open(os.path.basename(name)) as handle:
        handle.read()
    with open(secure_filename(name)) as handle:
        handle.read()
    return "ok"


@app.route("/os-calls")
def os_calls():
    source = request.args["src"]
    target = request.args["dst"]
    os.rename("/tmp/a", target)  # $ Alert[py/path-injection]
    os.replace("/tmp/b", target)  # $ Alert[py/path-injection]
    os.symlink("/tmp/c", target)  # $ Alert[py/path-injection]
    os.link("/tmp/d", target)  # $ Alert[py/path-injection]
    os.rename(source, "/tmp/e")  # $ Alert[py/path-injection]
    os.mkdir("/tmp/f", mode=int(source))
    return "ok"


@app.route("/shutil-calls")
def shutil_calls():
    source = request.args["src"]
    target = request.args["dst"]
    shutil.rmtree("/tmp/a", target)
    shutil.chown("/tmp/b", target)
    shutil.copy("/tmp/c", target)  # $ Alert[py/path-injection]
    shutil.move("/tmp/d", target)  # $ Alert[py/path-injection]
    shutil.rmtree(source)  # $ Alert[py/path-injection]
    shutil.make_archive(source, "zip")
    shutil.unpack_archive(source)
    return "ok"


@app.route("/pathlib-calls")
def pathlib_calls():
    name = request.args["name"]
    pathlib.Path(name).read_text()  # $ Alert[py/path-injection]
    (Path(ROOT) / name).read_bytes()  # $ Alert[py/path-injection]
    base = Path(ROOT) / name
    base.unlink()  # $ Alert[py/path-injection]
    # Um objeto qualquer com método de mesmo nome não é um `Path`.
    cache = {"a": name}
    cache.get("a")
    queue = [name]
    queue.pop()
    handler = Registry(name)
    handler.resolve()
    handler.stat()
    return "ok"


class Registry:
    def __init__(self, name):
        self.name = name

    def resolve(self):
        return self.name

    def stat(self):
        return self.name


@app.route("/upload", methods=["POST"])
def upload():
    target = request.args["target"]
    incoming = request.files["upload"]
    incoming.save(target)  # $ Alert[py/path-injection]
    request.files["other"].save(target)  # $ Alert[py/path-injection]
    return "ok"


@app.route("/save-other")
def save_other():
    target = request.args["target"]
    # `save` de um objeto qualquer não é o `FileStorage.save`.
    store = Store()
    store.save(target)
    return "ok"


class Store:
    def save(self, value):
        return value


class Report(BaseModel):
    folder: str
    title: str


@api.get("/report")
async def report_route(item: Report, plain: str):
    os.listdir(item.folder)  # $ Alert[py/path-injection]
    os.listdir(plain)  # $ Alert[py/path-injection]
    return {"ok": True}


@api.get("/files/{name}")
async def fastapi_files(name: str):
    return StarFileResponse(name)  # $ Alert[py/path-injection]


@api.get("/fast/{name}")
async def fastapi_fast(name: str):
    return FastFileResponse(path=name)  # $ Alert[py/path-injection]


def FileResponse(path):
    return path


@app.route("/own-file-response")
def own_file_response():
    name = request.args["name"]
    # `FileResponse` do projeto (ou do Django, que recebe o arquivo) não é a do Starlette.
    return FileResponse(name)


class Upload(BaseModel):
    folder: str
    size: int = 0


@api.post("/upload-helper")
async def upload_helper(payload: Upload):
    await store_upload(payload)


async def store_upload(payload: Upload):
    # O campo do modelo Pydantic continua contaminado na função anotada com a classe (Pydantic.qll).
    target = Path("/srv/uploads") / f"{payload.folder}/{payload.size}.bin"
    target.write_bytes(b"")  # $ Alert[py/path-injection]


@api.get("/parent/{name}")
async def parent_dir(name: str):
    target = Path("/srv/data") / name
    # O `parent` de um `Path` também é `Path` (pathlibPathAttribute).
    target.parent.mkdir(parents=True)  # $ Alert[py/path-injection]
    target.with_suffix(".tmp").touch()  # $ Alert[py/path-injection]


@login_required
def serve_file(request, path):
    # View do Django registrada no `urls.py` de outro arquivo: o decorador de view a identifica.
    return open(os.path.join("/srv/media", path))  # $ Alert[py/path-injection]
