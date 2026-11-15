function assigned(el) {
  sessionStorage.setItem("session", location.search);
  const saved = sessionStorage.getItem("session");
  el.innerHTML = saved;
}

function inline(el) {
  sessionStorage.setItem("session", location.search);
  el.innerHTML = sessionStorage.getItem("session");
}
