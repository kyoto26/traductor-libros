import { PageHeading, WorkTitle } from "./OpenBook";

export default function ProgressView({ fileName, pct, stageLabel, progress }) {
  const { translated, total } = progress;
  const width = `${pct}%`;

  return (
    <div className="flex flex-1 flex-col">
      <PageHeading>En traducción</PageHeading>
      <WorkTitle>{fileName}</WorkTitle>
      <div className="mt-1 text-xs text-brand-violet-core/50">Inglés → Español</div>

      <div
        className="mt-auto pt-10 font-display text-[120px] font-medium leading-[.9]"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        aria-valuetext={`${pct}% · ${stageLabel}`}
      >
        {pct}
        <span className="text-[44px] italic text-brand-violet-glow">%</span>
      </div>

      <div className="relative mt-[22px] h-0.5 bg-brand-violet-core/15">
        {/* Before there is a percentage, a fainter glint runs along the empty
            track so the bar never looks frozen. */}
        {pct === 0 && (
          <div className="absolute inset-0 overflow-hidden opacity-50">
            <span className="progress-glint absolute inset-0 animate-glint" />
          </div>
        )}
        <div
          className="progress-fill absolute left-0 top-0 h-0.5 animate-glow overflow-hidden"
          style={{ width }}
        >
          <span className="progress-glint absolute inset-0 animate-glint" />
        </div>
        <div
          className="progress-ribbon absolute -top-1 -ml-1.5 h-[30px] w-3 bg-brand-violet-glow"
          style={{ left: width }}
        />
      </div>

      <div className="mt-[22px] flex items-center justify-between gap-4 text-[13px] text-brand-violet-core/65">
        <span>{stageLabel}</span>
        {total > 0 && (
          <span className="text-brand-violet-core/50">
            {translated} / {total} bloques
          </span>
        )}
      </div>
    </div>
  );
}
