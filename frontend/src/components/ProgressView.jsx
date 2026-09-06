import StatusBadge from "./StatusBadge";

export default function ProgressView({ state, progress }) {
  const { translated, total } = progress;
  const hasTotal = typeof total === "number" && total > 0;
  const percent = hasTotal ? Math.min(100, Math.round((translated / total) * 100)) : 0;

  return (
    <div className="flex w-full max-w-md flex-col items-center gap-4">
      <StatusBadge status={state} />

      {hasTotal && (
        <span className="text-4xl font-bold text-brand-violet-core">{percent}%</span>
      )}

      <div className="h-3 w-full overflow-hidden rounded-full bg-brand-violet/15">
        <div
          className={`h-full rounded-full bg-brand-violet transition-all duration-500 ${
            hasTotal ? "" : "w-1/3 animate-pulse"
          }`}
          style={hasTotal ? { width: `${percent}%` } : undefined}
        />
      </div>

      <p className="text-sm text-brand-violet-glow">
        {hasTotal
          ? `${translated} / ${total} bloques traducidos`
          : "Preparando el documento..."}
      </p>
    </div>
  );
}
