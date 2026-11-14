/*
 * Full-bleed background: the ascii-magic "arctic-icebergs" piece (100x36
 * cells) is scaled so its canvas always covers the viewport — wider screens
 * get a larger cell instead of black bars.
 *
 * A text cell is CELL_W (0.602) of the font size wide and 1/CELL_W tall, so
 * the smallest font size that still covers the screen is:
 *     max(viewportWidth / cols, viewportHeight / (rows / CELL_W))
 */
const PIECE = { cols: 100, rows: 36, cellW: 0.602 };

const host = document.querySelector(".ascii-bg-layer ascii-art");

if (host) {
  let timer = 0;

  const fit = () => {
    timer = 0;
    const cellWidth = Math.max(
      window.innerWidth / PIECE.cols,
      window.innerHeight / (PIECE.rows / PIECE.cellW)
    );
    const size = Math.min(96, Math.max(3, cellWidth / PIECE.cellW));
    const next = size.toFixed(2);
    if (host.getAttribute("size") !== next) host.setAttribute("size", next);
  };

  const schedule = () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(fit, 180);
  };

  fit();
  window.addEventListener("resize", schedule, { passive: true });
  window.addEventListener("orientationchange", schedule, { passive: true });
}
