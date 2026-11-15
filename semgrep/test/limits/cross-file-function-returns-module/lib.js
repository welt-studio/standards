exports.pick = function (special) {
  return special ? require("fs") : require("original-fs");
};
