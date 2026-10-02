import { downloadUrl } from "../api";
import { PageHeading, WorkTitle } from "./OpenBook";
import StatusBadge from "./StatusBadge";

// Mirrors the Content-Disposition name built by GET /download/{job_id}.
// Reading the header directly would need a fetch plus a CORS expose_headers
// change, so the convention is duplicated here instead.
function downloadNameFor(fileName) {
  return `translated_${fileName}`;
}

function formatLabel(fileName) {
  const ext = fileName.split(".").pop();
  return ext ? ext.toUpperCase() : "";
}

export default function ResultView({ state, jobId, fileName, progress, error, onRetry, onReset }) {
  if (state === "completed") {
    const meta = ["Español", formatLabel(fileName)];
    if (progress.total > 0) {
      meta.push(`${progress.total.toLocaleString("es")} bloques`);
    }

    return (
      <div className="flex flex-1 flex-col">
        <PageHeading>Devolución</PageHeading>
        <div className="flex items-center gap-4">
          <div className="book-cover h-[70px] w-[52px] flex-none" />
          <div className="min-w-0">
            <WorkTitle>{downloadNameFor(fileName)}</WorkTitle>
            <div className="mt-1 text-xs text-brand-violet-core/55">{meta.filter(Boolean).join(" · ")}</div>
          </div>
        </div>

        <div className="mb-9 mt-[34px] flex flex-col">
          <StatusBadge status="completed" />
        </div>

        <a href={downloadUrl(jobId)} className="book-button mt-auto">
          <span>Descargar traducción</span>
          <span>↓</span>
        </a>
        <div className="mt-4 text-center">
          <button type="button" onClick={onReset} className="book-link">
            Traducir otro documento
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      <PageHeading>Incidencia</PageHeading>
      {fileName && <WorkTitle>{fileName}</WorkTitle>}
      <div className="mt-3.5 break-words font-mono text-[13px] leading-[1.55] text-brand-violet-light">
        {error}
      </div>

      <div className="mb-9 mt-[30px] flex flex-col">
        <StatusBadge status="failed" />
      </div>

      <button type="button" onClick={onRetry} disabled={!fileName} className="book-button mt-auto">
        <span>Reintentar</span>
        <span>↻</span>
      </button>
      <div className="mt-4 text-center">
        <button type="button" onClick={onReset} className="book-link">
          Elegir otro archivo
        </button>
      </div>
    </div>
  );
}
