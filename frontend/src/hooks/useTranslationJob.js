import { useCallback, useEffect, useRef, useState } from "react";
import { fetchStatus, uploadFile } from "../api";

const POLL_INTERVAL_MS = 2000;

const VIEW_BY_STATE = {
  idle: "upload",
  uploading: "progress",
  pending: "progress",
  processing: "progress",
  completed: "done",
  failed: "error",
};

// The stage is derived from real job state, not from percentage thresholds:
// extraction happens before total_blocks is known, and reconstruction runs
// after the last block is translated while the job is still "processing".
function stageLabelFor(state, translated, total) {
  if (state === "processing" && total > 0) {
    return translated < total ? "Traduciendo capítulos…" : "Reconstruyendo formato…";
  }
  return "Leyendo estructura…";
}

function percentFor(state, translated, total) {
  if (state === "completed") return 100;
  if (!(total > 0)) return 0;
  // Capped at 99 so the counter never reads 100% while reconstruction is
  // still running on the backend.
  return Math.min(99, Math.floor((translated / total) * 100));
}

export function useTranslationJob() {
  const [state, setState] = useState("idle");
  const [jobId, setJobId] = useState(null);
  const [progress, setProgress] = useState({ translated: 0, total: null });
  const [error, setError] = useState(null);
  const [file, setFile] = useState(null);

  const pollTimerRef = useRef(null);
  // The job this hook currently cares about. Responses for any other job
  // (e.g. a fetch still in flight when reset() ran) are ignored, so a stale
  // response can never resurrect polling.
  const activeJobRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const poll = useCallback(function pollStatus(currentJobId) {
    fetchStatus(currentJobId)
      .then((data) => {
        if (activeJobRef.current !== currentJobId) return;

        setProgress({ translated: data.translated_blocks, total: data.total_blocks });
        setState(data.status);

        if (data.status === "completed") {
          return;
        }
        if (data.status === "failed") {
          setError(data.error || "La traducción falló.");
          return;
        }

        pollTimerRef.current = setTimeout(() => pollStatus(currentJobId), POLL_INTERVAL_MS);
      })
      .catch((err) => {
        if (activeJobRef.current !== currentJobId) return;
        setError(err.message);
        setState("failed");
      });
  }, []);

  const submit = useCallback(
    async (selectedFile) => {
      stopPolling();
      const attempt = Symbol("upload");
      activeJobRef.current = attempt;

      setFile(selectedFile);
      setJobId(null);
      setError(null);
      setProgress({ translated: 0, total: null });
      setState("uploading");

      try {
        const newJobId = await uploadFile(selectedFile);
        if (activeJobRef.current !== attempt) return;
        activeJobRef.current = newJobId;
        setJobId(newJobId);
        setState("pending");
        poll(newJobId);
      } catch (err) {
        if (activeJobRef.current !== attempt) return;
        setError(err.message);
        setState("failed");
      }
    },
    [poll, stopPolling]
  );

  // Retry resubmits the file already in memory instead of making the user
  // pick it again after a failure.
  const retry = useCallback(() => {
    if (file) {
      submit(file);
    }
  }, [file, submit]);

  const reset = useCallback(() => {
    stopPolling();
    activeJobRef.current = null;
    setFile(null);
    setJobId(null);
    setProgress({ translated: 0, total: null });
    setError(null);
    setState("idle");
  }, [stopPolling]);

  useEffect(() => stopPolling, [stopPolling]);

  const { translated, total } = progress;

  return {
    state,
    view: VIEW_BY_STATE[state],
    jobId,
    progress,
    pct: percentFor(state, translated, total),
    stageLabel: stageLabelFor(state, translated, total),
    fileName: file?.name ?? null,
    error,
    submit,
    retry,
    reset,
  };
}
