import LibraryBackdrop from "./components/library/LibraryBackdrop";
import OpenBook from "./components/OpenBook";
import ProgressView from "./components/ProgressView";
import ResultView from "./components/ResultView";
import UploadForm from "./components/UploadForm";
import { useTranslationJob } from "./hooks/useTranslationJob";

export default function App() {
  const { state, view, jobId, progress, pct, stageLabel, fileName, error, submit, retry, reset } =
    useTranslationJob();

  return (
    <main className="relative box-border flex min-h-screen items-center justify-center overflow-hidden px-5 pb-20 pt-12">
      <LibraryBackdrop />

      <OpenBook view={view}>
        {view === "upload" && <UploadForm onSubmit={submit} />}

        {view === "progress" && (
          <ProgressView fileName={fileName} pct={pct} stageLabel={stageLabel} progress={progress} />
        )}

        {(view === "done" || view === "error") && (
          <ResultView
            state={state}
            jobId={jobId}
            fileName={fileName}
            progress={progress}
            error={error}
            onRetry={retry}
            onReset={reset}
          />
        )}
      </OpenBook>
    </main>
  );
}
