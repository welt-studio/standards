// own-test: js/html-constructed-from-input
// Classe exportada (PackageExports.qll): construtor, método e método estático públicos valem, e o
// `private`, o `protected`, o nome com `_` e a classe que ninguém exporta não.
export class Widget {
  constructor(heading: string) {
    document.body.innerHTML = "<h1>" + heading + "</h1>"; // $ Alert[js/html-constructed-from-input]
  }

  show(body: string, footer: string): void {
    document.body.innerHTML = "<footer>" + footer + "</footer>"; // $ Alert[js/html-constructed-from-input]
  }

  static build(label: string): void {
    document.body.innerHTML = "<span>" + label + "</span>"; // $ Alert[js/html-constructed-from-input]
  }

  private hidden(value: string): void {
    document.body.innerHTML = "<span>" + value + "</span>";
  }

  protected guarded(value: string): void {
    document.body.innerHTML = "<span>" + value + "</span>";
  }

  _underscore(value: string): void {
    document.body.innerHTML = "<span>" + value + "</span>";
  }
}

class Internal {
  run(value: string): void {
    document.body.innerHTML = "<span>" + value + "</span>";
  }
}
new Internal().run("fixo");
