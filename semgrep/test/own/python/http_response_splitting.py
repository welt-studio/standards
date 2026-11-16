# own-test: py/http-response-splitting
# Injeção de cabeçalho (py/http-response-splitting), conferida contra o HttpHeaderInjectionCustomizations.qll,
# Werkzeug.qll, Flask.qll, Stdlib.qll (http.server) e os modelos do Django, FastAPI, Tornado, Bottle
# e Aiohttp (que rejeitam quebra de linha e não têm sumidouro).
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler

from flask import Flask, Response, make_response, request
from werkzeug.datastructures import Headers

app = Flask(__name__)


@app.route("/flask-name")
def flask_name():
    label = request.args["label"]
    reply = make_response("ok")
    reply.headers["X-Label"] = label
    reply.headers[label] = "value"  # $ Alert[py/http-response-splitting]
    reply.headers.add("X-Other", label)
    reply.headers.add(label, "value")  # $ Alert[py/http-response-splitting]
    reply.headers.set(label, "value")  # $ Alert[py/http-response-splitting]
    return reply


@app.route("/flask-bulk")
def flask_bulk():
    label = request.args["label"]
    clean = request.args["clean"].replace("\n", "")
    kept_return = request.args["kept"].replace("\r", "")
    first = make_response("ok", {label: "value"})  # $ Alert[py/http-response-splitting]
    second = Response("ok", 200, {label: "value"})  # $ Alert[py/http-response-splitting]
    third = make_response("ok", headers=[(label, "value")])  # $ Alert[py/http-response-splitting]
    fourth = make_response("ok", {"X-Value": label})
    fifth = make_response("ok", {clean: "value"})
    sixth = make_response("ok", {kept_return: "value"})  # $ Alert[py/http-response-splitting]
    return first, second, third, fourth, fifth, sixth


@app.route("/flask-headers-object")
def flask_headers_object():
    label = request.args["label"]
    headers = Headers()
    headers.add("X-Value", label)
    headers.add(label, "value")  # $ Alert[py/http-response-splitting]
    return "ok"


@app.route("/flask-converted")
def flask_converted():
    count = int(request.args["count"])
    reply = make_response("ok", {count: "value"})
    return reply


@app.route("/not-flask-headers")
def not_flask_headers():
    label = request.args["label"]
    # Dicionário qualquer e `headers.update` não são escritas de cabeçalho no CodeQL.
    table = {}
    table[label] = "value"
    envelope = Envelope()
    envelope.headers.update({label: "value"})
    return "ok"


class Envelope:
    def __init__(self):
        self.headers = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        label = self.headers["X-Label"]
        target = self.path
        self.send_response(200)
        self.send_header("X-Label", label)  # $ Alert[py/http-response-splitting]
        self.send_header(target, "value")  # $ Alert[py/http-response-splitting]
        self.send_header("X-Safe", "fixed")
        self.end_headers()


class Extra(SimpleHTTPRequestHandler):
    def do_GET(self):
        value = self.headers["X-Value"]
        self.extra_response_headers = [("X-Value", value)]  # $ Alert[py/http-response-splitting]
        super().do_GET()


class Plain(BaseHTTPRequestHandler):
    def do_GET(self):
        value = self.headers["X-Value"]
        # O BaseHTTPRequestHandler não lê `extra_response_headers`.
        self.extra_response_headers = [("X-Value", value)]


class Local:
    def __init__(self, headers, path):
        self.headers = headers
        self.path = path

    def reply(self, writer):
        # `self.headers` e `self.path` de uma classe qualquer não vêm da requisição.
        writer.send_header("X-Label", self.headers["label"])
        writer.send_header(self.path, "value")
