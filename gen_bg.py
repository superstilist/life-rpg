import json
from pathlib import Path

frames_dir = Path("ascii_sr/background_max4x/frames")
frames = []
for p in sorted(frames_dir.glob("frame_*.txt")):
    frames.append(p.read_text(encoding="utf-8"))

lines = []
lines.append("/* Auto-generated upscaled background frames (ascii_sr) */")
lines.append("const BG_FPS = 12;")
lines.append("const BG_FRAMES = " + json.dumps(frames, ensure_ascii=False) + ";")
lines.append("""
(function () {
  const COLS = 320, ROWS = 96, CELL_W = 0.602;
  const layer = document.querySelector(".ascii-bg-layer");
  if (!layer) return;
  const pre = document.createElement("pre");
  pre.className = "ascii-bg-pre";
  pre.setAttribute("aria-hidden", "true");
  layer.appendChild(pre);

  const fit = () => {
    const cellWidth = Math.max(window.innerWidth / COLS, window.innerHeight / (ROWS / CELL_W));
    const size = Math.min(96, Math.max(3, cellWidth / CELL_W));
    pre.style.fontSize = size.toFixed(2) + "px";
  };
  fit();
  window.addEventListener("resize", fit, { passive: true });

  let i = 0;
  const render = () => { pre.textContent = BG_FRAMES[i]; i = (i + 1) % BG_FRAMES.length; };
  render();
  setInterval(render, 1000 / BG_FPS);
})();
""")
Path("game/static/game/ascii-bg-frames.js").write_text("\n".join(lines), encoding="utf-8")
print("frames:", len(frames))