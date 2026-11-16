// own-test: js/xss
// Mensagem recebida por WebSocket de cliente (`ClientWebSocket::ReceiveNode`, WebSocket.qll): o
// `data` do evento de uma instância de `new WebSocket(...)`, e o endereço escrito numa propriedade
// de um nó do DOM (`AttributeWriteUrlSink`).
class DownloadsUpdater {
  connect(wsUrl) {
    this.socket = new WebSocket(wsUrl);
    this.socket.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      const button = document.createElement("a");
      button.href = notification.link; // $ Alert[js/xss]
      button.innerHTML = notification.label; // $ Alert[js/xss]
    };
  }

  listen(wsUrl) {
    const feed = new WebSocket(wsUrl);
    feed.addEventListener("message", (event) => {
      document.querySelector("#feed").innerHTML = event.data; // $ Alert[js/xss]
    });
    feed.addEventListener("message", ({ data }) => {
      document.querySelector("#feed").innerHTML = data; // $ Alert[js/xss]
    });
  }

  // O `message` de um Worker ou de outra fonte que não é um WebSocket não é remoto.
  work(scriptUrl) {
    const worker = new Worker(scriptUrl);
    worker.onmessage = (event) => {
      document.querySelector("#feed").innerHTML = event.data;
    };
  }

  // A propriedade de um objeto qualquer não é um nó do DOM.
  configure(wsUrl) {
    const settings = { href: "" };
    const channel = new WebSocket(wsUrl);
    channel.onmessage = (event) => {
      settings.href = event.data;
    };
  }
}
