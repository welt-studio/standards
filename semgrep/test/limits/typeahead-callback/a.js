$(".typeahead").typeahead(
  {},
  {
    source(query, cb) {
      const target = document.location.search;
      cb(target);
    },
    templates: {
      suggestion(value) {
        return value;
      },
    },
  },
);

$(".typeahead").typeahead(
  {},
  {
    templates: {
      suggestion() {
        return document.location.search;
      },
    },
  },
);
