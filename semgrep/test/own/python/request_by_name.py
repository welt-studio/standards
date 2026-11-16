# own-test: py/path-injection
# A requisição HTTP vem do framework (tipo, view registrada, `flask.request`), nunca do nome.
from pydantic import BaseModel


class GenerationRequest(BaseModel):
    path: str


def build_request():
    return GenerationRequest(path="out.png")


def local_request_name():
    # Variável local chamada `request` não é a requisição HTTP.
    request = build_request()
    return open(request.path)


def typed_project_request(request: GenerationRequest):
    # Parâmetro anotado com uma classe do projeto que só se chama `...Request`.
    return open(request.path)


def unregistered_view(request, path):
    # Função sem registro, sem decorador e sem tipo: nada a liga ao framework.
    return open(path)
