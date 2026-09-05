const LABELS = {
  uploading: "Subiendo",
  pending: "En cola",
  processing: "Traduciendo",
  completed: "Completado",
  failed: "Error",
};

const STYLES = {
  uploading: "bg-brand-violet/20 text-brand-violet-glow animate-pulse",
  pending: "bg-brand-violet/20 text-brand-violet-glow animate-pulse",
  processing: "bg-brand-violet/30 text-brand-violet-glow animate-pulse",
  completed: "bg-brand-violet text-brand-black",
  failed: "bg-red-500/20 text-red-400",
};

export default function StatusBadge({ status }) {
  return (
    <span
      className={`inline-block w-fit rounded-full px-3 py-1 text-sm font-medium ${STYLES[status] ?? ""}`}
    >
      {LABELS[status] ?? status}
    </span>
  );
}
