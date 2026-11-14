angular
  .module("app", [])
  .factory("consumer", [
    "renderer",
    function (renderer) {
      renderer(window.location.search);
    },
  ])
  .factory("renderer", function () {
    return function (value) {
      $("<div>").html(value);
    };
  });

function direct(value) {
  $("<div>").html(value);
}
direct(window.location.search);
