# own-test: py/stack-trace-exposure
# Exposição de stack trace (py/stack-trace-exposure), conferida contra o ExceptionInfo.qll,
# StackTraceExposureCustomizations.qll, RestFramework.qll, FastApi.qll e Flask.qll do CodeQL.
import logging
import traceback

from fastapi import FastAPI
from flask import Flask, jsonify
from forms import ValidationError as ProjectValidationError
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from starlette.responses import JSONResponse, PlainTextResponse

app = Flask(__name__)
api = FastAPI()
log = logging.getLogger(__name__)


def compute():
    raise RuntimeError("segredo interno")


@app.route("/attributes")
def attributes():
    try:
        compute()
    except Exception as exc:
        return jsonify(exc.args)  # $ Alert[py/stack-trace-exposure]


@app.route("/attributes-detail")
def attributes_detail():
    try:
        compute()
    except Exception as exc:
        # Atributo da exceção é dado que ela carrega de propósito para o cliente.
        return jsonify(exc.detail)


@app.route("/helper-flow")
def helper_flow():
    try:
        compute()
    except Exception as exc:
        # A exceção inteira chega ao corpo pela função auxiliar.
        return render_failure(exc)  # $ Alert[py/stack-trace-exposure]


def render_failure(error):
    return {"message": error.message, "extra": error}


@app.route("/other-object")
def other_object():
    settings = {"title": "relatório"}
    try:
        compute()
    except Exception:
        log.exception("falhou")
        return jsonify(settings.get("title"))


@app.route("/container")
def container():
    errors = []
    try:
        compute()
    except Exception as exc:
        errors.append(str(exc))
    return jsonify(errors)  # $ Alert[py/stack-trace-exposure]


@app.route("/traceback-names")
def traceback_names():
    try:
        compute()
    except Exception:
        stack = traceback.format_exc()
        return jsonify(stack)  # $ Alert[py/stack-trace-exposure]


@app.route("/traceback-other")
def traceback_other():
    try:
        compute()
    except Exception:
        # `print_exc` e `walk_tb` não estão entre as funções do ExceptionInfo.qll.
        shown = traceback.walk_tb(None)
        return jsonify(shown)


@api.get("/starlette")
async def starlette_response():
    try:
        compute()
    except Exception as exc:
        # Além do CodeQL (decisão do PO): o Starlette.qll não modela estas respostas.
        return JSONResponse({"error": str(exc)})  # $ Alert[py/stack-trace-exposure]


@api.get("/starlette-plain")
async def starlette_plain():
    try:
        compute()
    except Exception as exc:
        return PlainTextResponse(str(exc))  # $ Alert[py/stack-trace-exposure]


@api.get("/starlette-fixed")
async def starlette_fixed():
    try:
        compute()
    except Exception as exc:
        log.error("falhou: %s", exc)
        return JSONResponse({"error": "falhou"})


def drf_view(request):
    try:
        compute()
    except Exception as exc:
        raise NotFound(str(exc))  # $ Alert[py/stack-trace-exposure]


def drf_response(request):
    try:
        compute()
    except Exception as exc:
        return Response({"error": str(exc)})  # $ Alert[py/stack-trace-exposure]


def local_exception_class(request):
    try:
        compute()
    except Exception as exc:
        # `ValidationError` de outro módulo não é a da API REST.
        raise LocalValidationError(str(exc))


class LocalValidationError(Exception):
    pass


def project_validation(request):
    try:
        compute()
    except Exception as exc:
        raise ProjectValidationError(str(exc))


@app.route("/helper-attribute")
def helper_attribute():
    try:
        compute()
    except Exception as exc:
        # Fora do `except` o atributo também não leva a exceção (leitura não é passo no CodeQL).
        return describe_failure(exc)


def describe_failure(error):
    return jsonify({"detail": error.detail})


@app.route("/method-call")
def method_call():
    try:
        compute()
    except Exception as exc:
        # Chamada de método é passo modelado: o texto da exceção continua.
        return jsonify(str(exc).strip())  # $ Alert[py/stack-trace-exposure]


def drf_reexport(value):
    try:
        compute()
    except Exception as exc:
        # `serializers.ValidationError` é a mesma da API, reexportada pelo DRF.
        raise serializers.ValidationError(str(exc)) from exc  # $ Alert[py/stack-trace-exposure]


@app.route("/exception-method")
def exception_method():
    try:
        compute()
    except Exception as exc:
        # Método da exceção (como o `errors()` do Pydantic) não é passo no CodeQL.
        return jsonify({"details": exc.errors()})
