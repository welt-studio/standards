angular.module("app", []).directive("widget", function () {
  return { templateUrl: Cookie.get("template") };
});

addEventListener("message", (ev) => {
  Cookie.set("template", ev.data);
});
