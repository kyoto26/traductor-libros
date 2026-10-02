import { memo } from "react";
import { MOTES, SHELVES } from "./shelves";

// Purely decorative layers: blurred shelves, warm ambient light, a light
// ray and floating dust. Memoized because none of it depends on job state.
function LibraryBackdrop() {
  return (
    <div aria-hidden="true">
      <div className="absolute -inset-1.5 flex flex-col justify-around opacity-95 blur-[1.6px]">
        {SHELVES.map((books, shelfIndex) => (
          <div
            key={shelfIndex}
            className="library-shelf flex h-[23vh] items-end gap-0.5 overflow-hidden px-2"
          >
            {books.map((book, bookIndex) => (
              <div
                key={bookIndex}
                className="library-book flex-none"
                style={{
                  width: `${book.width}px`,
                  height: `${book.height}%`,
                  background: book.background,
                }}
              />
            ))}
          </div>
        ))}
      </div>

      <div className="library-light absolute inset-0 animate-flicker" />
      <div className="library-ray pointer-events-none absolute -top-[10%] right-[14%] h-[120%] w-80" />

      {MOTES.map((mote, index) => (
        <div
          key={index}
          className="library-mote pointer-events-none absolute rounded-full"
          style={{
            left: `${mote.x}%`,
            top: `${mote.y}%`,
            width: `${mote.size}px`,
            height: `${mote.size}px`,
            "--o": mote.opacity,
            "--dx": `${mote.dx}px`,
            animation: `dust ${mote.duration}s linear ${mote.delay}s infinite`,
          }}
        />
      ))}
    </div>
  );
}

export default memo(LibraryBackdrop);
