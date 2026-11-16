# own-test: py/http-response-splitting
# Django e FastAPI rejeitam quebra de linha no nome e no valor do cabeçalho: no CodeQL não há
# sumidouro nesses frameworks (Django.qll, FastApi.qll), então nada aqui alerta.
from django.http import HttpResponse
from fastapi import FastAPI, Response

api = FastAPI()


def django_view(request, slug):
    # O Django rejeita quebra de linha no nome e no valor: não há sumidouro.
    reply = HttpResponse("ok")
    reply["X-Slug"] = slug
    reply[slug] = "value"
    return reply


@api.get("/fastapi/{label}")
async def fastapi_header(label: str, response: Response):
    response.headers[label] = "value"
    response.headers["X-Label"] = label
    return {"ok": True}
