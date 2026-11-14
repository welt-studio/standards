export function viaCallArgument(register) {
  let st = "";
  register((res) => {
    st = res;
  });
  $("#out").html(st);
}

export function viaObjectMethod(register) {
  let st = "";
  const cfg = useMemo(
    () => ({
      onData: (res) => {
        st = res;
      },
    }),
    [],
  );
  register(cfg);
  $("#out").html(st);
}
