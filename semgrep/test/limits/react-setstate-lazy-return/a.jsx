import { useState } from "react";

function lazy() {
  let [state, setState] = useState("initial");
  setState(() => document.location.search);
  return <div dangerouslySetInnerHTML={{ __html: state }} />;
}

function direct() {
  let [state, setState] = useState("initial");
  setState(document.location.search);
  return <div dangerouslySetInnerHTML={{ __html: state }} />;
}
