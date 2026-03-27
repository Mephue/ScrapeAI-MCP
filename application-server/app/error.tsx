"use client";

type ErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function Error({ error, reset }: ErrorProps) {
  return (
    <div className="min-h-screen bg-slate-50">
      <main className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6">
        <section className="surface p-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-red-600">Fehlerzustand</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">Die Analyse konnte nicht abgeschlossen werden.</h1>
          <p className="mt-3 text-sm leading-relaxed text-slate-600">
            Bitte versuche es erneut. Falls das Problem bleibt, pruefe den Data-Analytics-Service oder lade ein klareres Bild hoch.
          </p>
          <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error.message || "Unbekannter Fehler"}
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent-dark"
              onClick={reset}
            >
              Erneut versuchen
            </button>
            <button
              type="button"
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              onClick={() => window.location.assign("/")}
            >
              Zur Startseite
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}
