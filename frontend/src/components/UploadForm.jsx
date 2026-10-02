import { useRef, useState } from "react";
import { PageHeading } from "./OpenBook";

const ACCEPTED_EXTENSIONS = [".txt", ".epub", ".pdf"];

const FIELD_LABEL = "text-[11px] uppercase tracking-[.16em] text-brand-violet-core/55";
const FIELD_VALUE =
  "border-b-[1.5px] border-brand-violet-glow/55 pb-2.5 pt-1.5 font-display text-2xl font-medium italic";

export default function UploadForm({ onSubmit }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const inputRef = useRef(null);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (selectedFile) {
      onSubmit(selectedFile);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-1 flex-col">
      <PageHeading>Ficha de traducción</PageHeading>

      <div className={`${FIELD_LABEL} mb-2`}>Obra</div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(",")}
        onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
        className="hidden"
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="flex cursor-pointer items-baseline justify-between gap-3 border-0 border-b-[1.5px] border-brand-violet-glow/55 bg-transparent px-0 pb-3 pt-1.5 text-left transition-colors hover:border-brand-violet-core"
      >
        <span
          className={`truncate font-display text-[26px] italic ${
            selectedFile ? "text-brand-violet-core" : "text-brand-violet-core/45"
          }`}
        >
          {selectedFile ? selectedFile.name : "Elige tu archivo"}
        </span>
        <span className="flex-none text-xs text-brand-violet-glow">
          {selectedFile ? "Cambiar" : "Explorar"}
        </span>
      </button>
      <div className="mt-2.5 text-xs text-brand-violet-core/50">EPUB, PDF o TXT · hasta 50 MB</div>

      {/* Fixed language pair: the backend only translates en->es today. */}
      <div className="mb-9 mt-[34px] grid grid-cols-[1fr_auto_1fr] items-end gap-3.5">
        <div className="flex flex-col gap-1.5">
          <span className={FIELD_LABEL}>De</span>
          <span className={FIELD_VALUE}>Inglés</span>
        </div>
        <span className="pb-2.5 font-display text-[26px] text-brand-violet-glow">→</span>
        <div className="flex flex-col gap-1.5">
          <span className={FIELD_LABEL}>A</span>
          <span className={FIELD_VALUE}>Español</span>
        </div>
      </div>

      <button type="submit" disabled={!selectedFile} className="book-button mt-auto">
        <span>Comenzar traducción</span>
        <span>→</span>
      </button>
    </form>
  );
}
