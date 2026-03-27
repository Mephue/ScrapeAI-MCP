export default function Loading() {
  return (
    <div className="min-h-screen bg-slate-50">
      <main className="mx-auto w-full max-w-5xl space-y-4 px-4 py-6 sm:px-6">
        <section className="surface p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Ladevorgang</p>
          <h1 className="mt-2 text-xl font-semibold text-slate-900">Daten werden geladen...</h1>
          <div className="mt-4 h-3 animate-pulse rounded-full bg-slate-200" />
          <div className="mt-3 h-3 w-1/2 animate-pulse rounded-full bg-slate-200" />
        </section>
        <section className="surface p-5">
          <h2 className="text-base font-semibold text-slate-900">Empfehlungen werden vorbereitet</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, idx) => (
              <article className="rounded-xl border border-slate-200 bg-white p-4" key={idx}>
                <div className="h-3 animate-pulse rounded-full bg-slate-200" />
                <div className="mt-3 h-3 w-2/3 animate-pulse rounded-full bg-slate-200" />
                <div className="mt-4 h-12 animate-pulse rounded-lg bg-slate-100" />
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
