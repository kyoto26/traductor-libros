const LEFT_PAGE = {
  upload: {
    eyebrow: "Traductor de documentos",
    title: "Cada libro,",
    titleAccent: "en tu idioma.",
    body: "Sube un documento y lo traducimos conservando capítulos, párrafos y formato.",
  },
  progress: {
    eyebrow: "Traduciendo",
    title: "Pasando",
    titleAccent: "las páginas…",
    body: "No cierres ni recargues esta pestaña: si lo haces, perderás el progreso de la traducción.",
  },
  done: {
    eyebrow: "Traducción lista",
    title: "Tu libro",
    titleAccent: "está listo.",
    body: "Traducción completada. El formato original se conservó.",
  },
  error: {
    eyebrow: "Algo salió mal",
    title: "Una página",
    titleAccent: "se nos perdió.",
    body: "Tu archivo original no se ha modificado.",
  },
};

export default function OpenBook({ view, children }) {
  const page = LEFT_PAGE[view];

  return (
    <div className="open-book relative grid w-full max-w-[940px] grid-cols-[repeat(auto-fit,minmax(310px,1fr))]">
      {/* Spine shadow; hidden once the pages stack into a single column. */}
      <div className="open-book-gutter pointer-events-none absolute bottom-0 left-1/2 top-0 -ml-[35px] hidden w-[70px] min-[560px]:block" />

      <section className="page-left relative flex min-h-[480px] flex-col px-12 pb-11 pt-[52px]">
        <div className="mb-auto text-[11px] uppercase tracking-[.26em] text-brand-violet-glow">
          {page.eyebrow}
        </div>
        <div className="mt-9">
          <h1 className="m-0 mb-5 font-display text-[60px] font-semibold leading-[.98] tracking-[-.015em]">
            {page.title}
            <br />
            <em className="font-medium text-brand-violet-glow">{page.titleAccent}</em>
          </h1>
          <p className="m-0 max-w-[300px] text-[15px] leading-[1.65] text-brand-violet-core/[.74]">
            {page.body}
          </p>
        </div>
        <div className="mt-9 flex items-center gap-2.5 font-display text-base italic text-brand-violet-core/50">
          <span className="h-px w-[22px] bg-brand-violet-glow/60" />
          Ex libris Acervo
        </div>
      </section>

      <section className="page-right relative flex flex-col px-12 pb-11 pt-[52px]">{children}</section>
    </div>
  );
}

// Small-caps heading shared by every right-hand page.
export function PageHeading({ children }) {
  return (
    <div className="mb-[22px] font-display text-[13px] uppercase tracking-[.3em] text-brand-violet-core/55">
      {children}
    </div>
  );
}

export function WorkTitle({ children }) {
  return (
    <div className="truncate font-display text-[26px] italic" title={children}>
      {children}
    </div>
  );
}
