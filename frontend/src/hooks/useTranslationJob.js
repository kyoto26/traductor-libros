import { useCallback, useEffect, useRef, useState } from "react";
import { fetchStatus, uploadFile } from "../api";

const POLL_INTERVAL_MS = 2000;

export function useTranslationJob() {
  const [state, setState] = useState("idle");
  const [jobId, setJobId] = useState(null);
  const [progress, setProgress] = useState({ translated: 0, total: null });
  const [error, setError] = useState(null);

  const fileRef = useRef(null);
  const pollTimerRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const poll = useCallback(
    (currentJobId) => {
      fetchStatus(currentJobId)
        .then((data) => {
          setProgress({ translated: data.translated_blocks, total: data.total_blocks });
          setState(data.status);

          if (data.status === "completed") {
            return;
          }
          if (data.status === "failed") {
            setError(data.error || "La traducción falló.");
            return;
          }

          pollTimerRef.current = setTimeout(() => poll(currentJobId), POLL_INTERVAL_MS);
        })
        .catch((err) => {
          setError(err.message);
          setState("failed");
        });
    },
    []
  );

  const submit = useCallback(
    async (file) => {
      fileRef.current = file;
      setError(null);
      setProgress({ translated: 0, total: null });
      setState("uploading");

      try {
        const newJobId = await uploadFile(file);
        setJobId(newJobId);
        setState("pending");
        poll(newJobId);
      } catch (err) {
        setError(err.message);
        setState("failed");
      }
    },
    [poll]
  );

  // "Intentar de nuevo" reenvía el mismo archivo que ya se había
  // seleccionado — no tiene sentido obligar al usuario a volver a elegirlo
  // del input tras un fallo si todavía lo tenemos en memoria.
  const retry = useCallback(() => {
    if (fileRef.current) {
      submit(fileRef.current);
    }
  }, [submit]);

  const reset = useCallback(() => {
    stopPolling();
    fileRef.current = null;
    setJobId(null);
    setProgress({ translated: 0, total: null });
    setError(null);
    setState("idle");
  }, [stopPolling]);

  useEffect(() => stopPolling, [stopPolling]);

  return { state, jobId, progress, error, submit, retry, reset };
}
