function control(ctx, el) {
  el.innerHTML = ctx.query.name;
}

export async function getServerSideProps(ctx) {
  const name = ctx.query.name;
  return { props: name };
}

export default function Page(props) {
  document.body.innerHTML = props;
  return null;
}
