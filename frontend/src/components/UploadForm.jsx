import { useState } from "react";

const ACCEPTED_EXTENSIONS = [".txt", ".epub", ".pdf"];

export default function UploadForm({ onSubmit }) {
  const [selectedFile, setSelectedFile] = useState(null);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (selectedFile) {
      onSubmit(selectedFile);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-md flex-col gap-6">
      {/* Selector de idioma fijo: el backend hoy solo traduce en->es */}
      <div className="flex items-center justify-between rounded-lg border border-brand-violet/40 bg-brand-violet/10 px-4 py-2 text-sm">
        <span className="text-brand-violet-glow">Idioma</span>
        <span className="font-medium">Inglés → Español</span>
      </div>

      <label className="flex flex-col gap-2">
        <span className="text-sm text-brand-violet-glow">Archivo (.txt, .epub, .pdf)</span>
        <input
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(",")}
          onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          className="cursor-pointer rounded-lg border border-brand-violet/40 bg-transparent px-4 py-3 text-sm file:mr-4 file:cursor-pointer file:rounded-md file:border-0 file:bg-brand-violet file:px-4 file:py-2 file:font-medium file:text-brand-black"
        />
      </label>

      <button
        type="submit"
        disabled={!selectedFile}
        className="rounded-lg bg-brand-violet px-6 py-3 font-semibold text-brand-black transition hover:bg-brand-violet-glow disabled:cursor-not-allowed disabled:opacity-40"
      >
        Traducir
      </button>
    </form>
  );
}
