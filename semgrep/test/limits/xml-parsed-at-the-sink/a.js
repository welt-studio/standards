module.exports.control = function (text) {
  const doc = new DOMParser().parseFromString(text, "text/xml");
  document.body.appendChild(doc.documentElement);
};

module.exports.parsed = function (text) {
  const doc = new DOMParser().parseFromString(text, "text/xml");
  const holder = document.createElement("div");
  holder.appendChild(doc.documentElement);
  holder.className = "xml";
  holder.title = "documento";
  holder.dataset.kind = "xml";
  document.body.appendChild(holder);
};
