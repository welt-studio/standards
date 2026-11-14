export function writtenInOneBranch() {
  const target = document.location.search;
  if (random()) {
    target.field = "safe";
  }
  $("#out").html(target.field);
}

export function neverWritten() {
  const target = document.location.search;
  $("#out").html(target.field);
}
