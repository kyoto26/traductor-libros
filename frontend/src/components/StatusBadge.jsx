// Rubber-stamp mark shown on the result page. The static rotate keeps the
// tilt when reduced motion disables the stamp animation.
const STAMPS = {
  completed: {
    label: "TRADUCIDO",
    className: "border-brand-violet-glow shadow-[inset_0_0_0_2px_rgba(5,5,5,.9),inset_0_0_0_3px_rgba(199,125,255,.6)]",
  },
  failed: {
    label: "INCOMPLETO",
    className: "border-brand-violet shadow-[inset_0_0_0_2px_rgba(5,5,5,.9),inset_0_0_0_3px_rgba(157,78,221,.7)]",
  },
};

export default function StatusBadge({ status }) {
  const stamp = STAMPS[status];
  if (!stamp) return null;

  return (
    <div
      className={`mr-2.5 self-end rotate-[-9deg] animate-stamp rounded border-[3px] px-[18px] py-1.5 font-display text-[26px] font-bold tracking-[.24em] text-brand-violet-glow opacity-95 ${stamp.className}`}
    >
      {stamp.label}
    </div>
  );
}
