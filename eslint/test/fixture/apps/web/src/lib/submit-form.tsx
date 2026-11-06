// Caso: handler async em atributo JSX (como o `onSubmit={form.handleSubmit(onValid)}` do
// react-hook-form) passa no `no-misused-promises`.
async function save(): Promise<void> {
  await Promise.resolve();
}

export function SubmitForm() {
  return <form onSubmit={save} />;
}
