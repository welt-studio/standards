import { useState } from "react";

export function laterSetterFeedsTheCallback() {
  const [state, setState] = useState("initial");
  setState((prev) => {
    $("#out").html(prev);
  });
  setState(document.location.search);
  return state;
}

export function earlierSetterFeedsTheCallback() {
  const [state, setState] = useState("initial");
  setState(document.location.search);
  setState((prev) => {
    $("#out").html(prev);
  });
  return state;
}
