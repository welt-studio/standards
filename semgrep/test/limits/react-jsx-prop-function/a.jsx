function Child(props) {
  const provide = props.provide;
  return <div dangerouslySetInnerHTML={{ __html: provide() }} />;
}

function Parent() {
  const source = document.location.search;
  return <Child provide={() => source} />;
}

function Direct() {
  const source = document.location.search;
  return <div dangerouslySetInnerHTML={{ __html: source }} />;
}
