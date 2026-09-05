import { downloadUrl } from "../api";

export default function ResultView({ state, jobId, error, onRetry, onReset }) {
  if (state === "completed") {
    return (
      <div className="flex w-full max-w-md flex-col items-center gap-4 text-center">
        <p className="text-brand-violet-core">¡Traducción lista!</p>
        <a
          href={downloadUrl(jobId)}
          className="rounded-lg bg-brand-violet px-6 py-3 font-semibold text-brand-black transition hover:bg-brand-violet-glow"
        >
          Descargar
        </a>
        <button onClick={onReset} className="text-sm text-brand-violet-glow underline">
          Traducir otro archivo
        </button>
      </div>
    );
  }

  return (
    <div className="flex w-full max-w-md flex-col items-center gap-4 text-center">
      <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-red-300">
        {error}
      </p>
      <div className="flex gap-3">
        <button
          onClick={onRetry}
          className="rounded-lg bg-brand-violet px-6 py-3 font-semibold text-brand-black transition hover:bg-brand-violet-glow"
        >
          Intentar de nuevo
        </button>
        <button
          onClick={onReset}
          className="rounded-lg border border-brand-violet/40 px-6 py-3 text-brand-violet-glow"
        >
          Elegir otro archivo
        </button>
      </div>
    </div>
  );
}
