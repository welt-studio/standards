// own-test: js/xss
// Angular (js/xss): do `DomSanitizer` só o `bypassSecurityTrustHtml` e o `Style` são sumidouros de
// XSS no DOM; o `Script`, o `Url` e o `ResourceUrl` são de outras consultas (Angular2.qll do CodeQL).
import { Component } from "@angular/core";
import { DomSanitizer } from "@angular/platform-browser";
import { ActivatedRoute } from "@angular/router";

class Banner {
  bypassSecurityTrustHtml(value: string): string {
    return value;
  }
}

@Component({ selector: "app-note", template: "" })
export class NoteComponent {
  constructor(
    private route: ActivatedRoute,
    private sanitizer: DomSanitizer,
    private banner: Banner,
  ) {}

  show() {
    const fragment = this.route.snapshot.fragment;
    this.sanitizer.bypassSecurityTrustHtml(fragment); // $ Alert[js/xss]
    this.sanitizer.bypassSecurityTrustStyle(fragment); // $ Alert[js/xss]
    this.sanitizer.bypassSecurityTrustScript(fragment);
    this.sanitizer.bypassSecurityTrustUrl(fragment);
    this.sanitizer.bypassSecurityTrustResourceUrl(fragment);
    this.banner.bypassSecurityTrustHtml(fragment);
  }
}
