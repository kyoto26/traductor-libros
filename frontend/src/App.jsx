import ProgressView from "./components/ProgressView";
import ResultView from "./components/ResultView";
import UploadForm from "./components/UploadForm";
import { useTranslationJob } from "./hooks/useTranslationJob";

export default function App() {
  const { state, jobId, progress, error, submit, retry, reset } = useTranslationJob();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-10 px-4 py-16">
      <header className="text-center">
        <h1 className="text-3xl font-bold text-brand-violet-core">Traductor de Documentos</h1>
        <p className="mt-2 text-brand-violet-glow">Traduce tus libros favoritos, sin perder su esencia</p>
      </header>

      {state === "idle" && <UploadForm onSubmit={submit} />}

      {(state === "uploading" || state === "pending" || state === "processing") && (
        <ProgressView state={state} progress={progress} />
      )}

      {(state === "completed" || state === "failed") && (
        <ResultView state={state} jobId={jobId} error={error} onRetry={retry} onReset={reset} />
      )}
    </div>
  );
}
