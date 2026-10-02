// Deterministic data for the library backdrop, ported 1:1 from the
// reference design. A fixed seed keeps every render (and every visit)
// showing the exact same shelves.

const SHELF_COUNT = 4;
const BOOKS_PER_SHELF = 46;
const MOTE_COUNT = 26;

const SPINE_COLORS = [
  "#33173f", "#4d2369", "#26122f", "#5d2d82", "#6d38a0",
  "#2c1539", "#7a3f58", "#4a2236", "#8a5a44", "#3a2a5a",
];

// Park-Miller minimal standard PRNG, seed 7 (same as the design).
function createRandom(seed) {
  let s = seed;
  return () => (s = (s * 16807) % 2147483647) / 2147483647;
}

function buildShelves() {
  const random = createRandom(7);

  return Array.from({ length: SHELF_COUNT }, () =>
    Array.from({ length: BOOKS_PER_SHELF }, () => {
      const color = SPINE_COLORS[Math.floor(random() * SPINE_COLORS.length)];
      const y = 12 + Math.floor(random() * 18);
      const gilt = random() > 0.4 ? "rgba(243,214,160,.55)" : "rgba(243,232,255,.3)";
      const bands =
        `linear-gradient(180deg,transparent ${y}%,${gilt} ${y}%,${gilt} ${y + 3}%,` +
        `transparent ${y + 3}%,transparent ${y + 70}%,${gilt} ${y + 70}%,` +
        `${gilt} ${y + 72}%,transparent ${y + 72}%)`;

      return {
        width: 16 + Math.floor(random() * 26),
        height: 62 + Math.floor(random() * 38),
        background: `${bands},linear-gradient(90deg,rgba(255,255,255,.1),transparent 35%,rgba(0,0,0,.35)),${color}`,
      };
    })
  );
}

function buildMotes() {
  return Array.from({ length: MOTE_COUNT }, (_, i) => ({
    x: 45 + ((i * 37) % 50),
    y: 15 + ((i * 53) % 75),
    size: 2 + (i % 3),
    opacity: (0.35 + (i % 4) * 0.15).toFixed(2),
    dx: (i % 2 ? 1 : -1) * (20 + ((i * 7) % 50)),
    duration: 9 + (i % 7) * 2,
    delay: -(i * 1.3),
  }));
}

export const SHELVES = buildShelves();
export const MOTES = buildMotes();
