/*
 * Arctic Icebergs — based on the ASCII Magic piece by ASCII Magic.
 * Copyright (c) 2026 ASCII Magic (ascii-magic.com)
 * Licensed under the MIT License; see ../LICENSE.
 */
import { Grid, palette, gradient, KEYS, fbm, noise2, rng, clamp } from "../lib/kit.js";

const SCALE = 2;
const SOURCE_COLS = 100;
const SOURCE_ROWS = 36;
const SOURCE_HORIZON = 21;
const LOOP_SECONDS = 10;

// Edit these one-cell glyphs, or override them with create({ symbols: { ... } }).
export const SYMBOLS = {
  stars: ["·", "◦", "•", "*", "+"],
  auroraDense: "▓", auroraMid: "▒", auroraLight: "░", auroraSpark: "•", auroraGlint: "·", skyDust: "◦",
  waterDense: "▓", waterMid: "▒", waterLight: "░", waterLine: "-", waterGlint: "·", waterSpark: "•",
  waterPearl: "◦", waterSquare: "▪",
  iceDense: "▓", iceSolid: "█", iceMid: "▒", iceCrystal: "·", iceGem: "▪",
  crackSlash: "╱", crackBackslash: "╲", reflectionLight: "░", reflectionMid: "▒", iceSurface: "▀",
};

const SAFE_SYMBOLS = "·•●○◦■□▪▫◆◇▲△▼▽◀▶►◄≈≡°✓✗♥×÷±→←↑↓↗↘↙↖⟋⟍";
const oneCell = (glyph) => {
  if (typeof glyph !== "string" || [...glyph].length !== 1) return false;
  const code = glyph.codePointAt(0);
  return (code >= 32 && code <= 126)
    || (code >= 0x2500 && code <= 0x259f)
    || (code >= 0x2800 && code <= 0x28ff)
    || SAFE_SYMBOLS.includes(glyph);
};
function resolveSymbols(overrides = {}) {
  const out = {};
  for (const [key, fallback] of Object.entries(SYMBOLS)) {
    const value = overrides && overrides[key];
    if (Array.isArray(fallback)) {
      const candidate = Array.isArray(value) ? value : typeof value === "string" ? [...value] : fallback;
      const safe = candidate.filter(oneCell);
      out[key] = safe.length ? safe : fallback;
    } else out[key] = oneCell(value) ? value : fallback;
  }
  return out;
}

const choose = (glyphs, value) => glyphs[Math.min(glyphs.length - 1, Math.floor(value * glyphs.length))];

const P = [];
const add = (a) => { const o = P.length; P.push(...a); return o; };
const SKY = add(gradient(["#03060f", "#071428", "#0e2240", "#1a3458"], 8));
const AUR = add(gradient(["#0e4a3a", "#1a8a5a", "#3ad08a", "#9af0c0"], 6));
const ICE = add(gradient(["#1a3a5a", "#3a6a94", "#7aa8cc", "#bcdcef", "#f2fbff"], 10));
const SEA = add(gradient(["#02050c", "#06111f", "#0c2034", "#173350"], 6));
const SUB = add(["#0e3a52", "#1a5a72"]);
const STAR = add(["#8090b0", "#e0e8ff"]);

export const meta = {
  slug: "arctic-icebergs",
  name: "Arctic Icebergs",
  category: "landscapes",
  note: "Icebergs drift on a dark polar sea under a faint green aurora, the swell rolling past them.",
  tags: ["nature", "arctic", "ice", "ocean", "aurora", "wallpaper"],
  cols: SOURCE_COLS * SCALE, rows: SOURCE_ROWS * SCALE, fps: 50, loopSeconds: LOOP_SECONDS,
  dots: { size: 0.53, density: 1.35, tone: { lo: 0.04, hi: 0.985, curve: 1.1, sat: 0.85 } },
  palette: palette(P),
};

export default function create(options = {}) {
  const S = resolveSymbols(options.symbols);
  const { cols, rows } = meta;
  const g = new Grid(cols, rows);
  const r = rng(61);
  const hz = SOURCE_HORIZON * SCALE;
  const stars = Array.from(
    { length: 70 * SCALE * SCALE },
    () => [Math.floor(r() * cols), Math.floor(r() * (hz - 2 * SCALE)), r(), r() * 6.28],
  );

  // Icebergs: jagged profiles, [center, half-width, height, seed, bob phase].
  // Existing noise is sampled in source-grid coordinates; a small deterministic
  // perturbation only fills the new half-cell samples in the 2x profile.
  const bergs = [[22, 16, 11, 1, 0], [62, 9, 6, 2, 2], [84, 12, 9, 3, 4], [44, 4, 3, 4, 1]].map(
    ([cx0, w0, h0, seed, ph]) => {
      const cx = cx0 * SCALE;
      const w = w0 * SCALE;
      const h = h0 * SCALE;
      const prof = [];
      for (let i = -w; i <= w; i++) {
        const sourceI = i / SCALE;
        const u = i / w;
        const base = h * Math.pow(Math.max(0, 1 - u * u), 0.35)
          * (0.6 + 0.45 * noise2(sourceI * 0.2, seed * 3, 4));
        const jag = (noise2(sourceI * 0.5, seed * 10, 7) - 0.5) * h * 0.3;
        const fineRidge = i % SCALE === 0
          ? 0
          : (noise2(i * 0.35, seed * 13, 29) - 0.5) * h * 0.035;
        prof.push(Math.max(0, base + jag + fineRidge));
      }
      return { cx, w, h, sourceW: w0, sourceH: h0, seed, prof, ph };
    },
  );

  return (t) => {
    const cycleT = ((t % LOOP_SECONDS) + LOOP_SECONDS) % LOOP_SECONDS;
    const motionT = (1 - Math.cos((cycleT / LOOP_SECONDS) * Math.PI * 2)) * LOOP_SECONDS * 0.5;
    g.clear();

    // Night sky and aurora. All original waves and noise use source-grid units.
    for (let y = 0; y < hz; y++) for (let x = 0; x < cols; x++) {
      const sx = x / SCALE;
      const sy = y / SCALE;
      const v = sy / SOURCE_HORIZON;
      const curtainY = 5 + Math.sin(sx * 0.06 + motionT * 0.25) * 2.5
        + Math.sin(sx * 0.021 - motionT * 0.15) * 2;
      const rays = fbm(sx * 0.25 + motionT * 0.15, motionT * 0.1, 2, 13);
      const a = Math.exp(-(((sy - curtainY) / (3 + rays * 3)) ** 2))
        * (0.3 + rays) * (0.65 + 0.35 * Math.sin(motionT * 0.4 + sx * 0.03));
      const fineBand = (noise2(x * 0.12 + motionT * 0.035, y * 0.18 + motionT * 0.02, 37) - 0.5) * 0.035;
      const band = a + fineBand;
      const filament = noise2(x * 0.19 + motionT * 0.025, y * 0.23 + motionT * 0.015, 71);
      const auroraGlyph = band > 0.75 ? (filament > 0.94 ? S.auroraSpark : S.auroraDense)
        : band > 0.5 ? (filament > 0.93 ? S.auroraGlint : S.auroraMid)
          : filament > 0.99 ? S.skyDust : S.auroraLight;
      if (band > 0.32) g.set(x, y, auroraGlyph, KEYS[AUR + clamp(Math.floor(band * 6), 0, 5)]);
      else if (filament > 0.997 && y < hz * 0.72) g.set(x, y, S.skyDust, KEYS[SKY + clamp(Math.floor(v * 7 + rays), 0, 7)]);
      else g.set(x, y, v > 0.6 ? S.auroraMid : S.auroraLight, KEYS[SKY + clamp(Math.floor(v * 7 + rays), 0, 7)]);
    }

    for (const [sx, sy, b, ph] of stars) {
      const ki = KEYS.indexOf(g.co[sx + sy * cols]);
      if (ki >= AUR && ki < AUR + 6) continue;
      if (Math.sin(motionT * 1.5 + ph) > -0.3) {
        const starGlyph = choose(S.stars, b);
        g.set(sx, sy, starGlyph, KEYS[STAR + (b > 0.6 ? 1 : 0)]);
      }
    }

    // Rolling sea with the original swell and aurora reflection at normalized
    // coordinates, plus sparse, fixed fine highlights on the larger grid.
    for (let y = hz; y < rows; y++) {
      const sy = y / SCALE;
      const d = (sy - SOURCE_HORIZON) / (SOURCE_ROWS - SOURCE_HORIZON);
      for (let x = 0; x < cols; x++) {
        const sx = x / SCALE;
        const w = fbm(sx * 0.06 - motionT * 0.25, sy * 0.5 + motionT * 0.15, 3, 3);
        const swell = Math.sin(sx * 0.12 + sy * 0.9 - motionT * 1.6) * 0.15;
        const aur = Math.exp(-(((sx - SOURCE_COLS / 2 - Math.sin(motionT * 0.25) * 20) / 30) ** 2))
          * (w > 0.55 ? 1 : 0) * (1 - d);
        const v = clamp(0.35 + d * 0.3 + (w - 0.5) * 0.7 + swell);
        const glint = noise2(x * 0.21, y * 0.28, 47);
        const pearl = noise2(x * 0.34, y * 0.38, 73);
        if (aur > 0.45) g.set(x, y, S.waterLine, KEYS[AUR + 2]);
        else if (glint > 0.965 && w > 0.58 && v > 0.5 && swell > 0.015) g.set(x, y, glint > 0.994 ? S.waterSpark : S.waterGlint, KEYS[SEA + 5]);
        else if (pearl > 0.996 && v > 0.42) g.set(x, y, pearl > 0.998 ? S.waterSquare : S.waterPearl, KEYS[SEA + clamp(Math.floor(v * 6), 0, 5)]);
        else g.set(x, y, v > 0.6 ? S.waterDense : v > 0.35 ? S.waterMid : S.waterLight, KEYS[SEA + clamp(Math.floor(v * 6), 0, 5)]);
      }
    }

    // Icebergs, submerged shelves, and reflections all keep their source-scale
    // motion. Added facet grain and fine cracks are deterministic in material space.
    for (const b of bergs) {
      const bob = Math.sin(motionT * 0.9 + b.ph) * 0.6 * SCALE;
      const drift = Math.sin(motionT * 0.05 + b.ph) * 3 * SCALE;
      for (let i = 0; i < b.prof.length; i++) {
        const x = Math.round(b.cx + drift) + i - b.w;
        const top = hz - b.prof[i] + bob;
        const topRow = Math.floor(top);
        const slope = (b.prof[Math.min(b.prof.length - 1, i + 1)]
          - b.prof[Math.max(0, i - 1)]) / SCALE;
        const u = (i - b.w) / b.w;
        for (let y = topRow; y < hz; y++) {
          const depth = y - top;
          const sourceDepth = depth / SCALE;
          const materialDepth = (y - (hz - b.prof[i])) / SCALE;
          const sourceX = x / SCALE;
          const sourceY = y / SCALE;
          const facet = (noise2(i * 0.24, materialDepth * 0.38, b.seed + 31) - 0.5) * 0.075;
          const lit = clamp(0.62 - u * 0.4 - sourceDepth * 0.035 + slope * 0.06
            + (noise2(sourceX * 0.4, sourceY * 0.7, 3) - 0.5) * 0.3
            + facet + (y === topRow ? 0.2 : 0));
          let glyph = lit > 0.75 ? S.iceSolid : lit > 0.45 ? S.iceDense : S.iceMid;
          let color = KEYS[ICE + clamp(Math.floor(lit * 10), 0, 9)];
          const crystal = noise2(i * 0.33, materialDepth * 0.72, b.seed + 73);
          if (crystal > 0.992 && sourceDepth > 1.2 && lit > 0.48) glyph = crystal > 0.998 ? S.iceGem : S.iceCrystal;

          const localX = (i - b.w) / SCALE;
          const crackX = -b.sourceW * 0.2 + Math.sin(materialDepth * 0.7 + b.ph) * 0.15;
          const crackNoise = noise2(materialDepth * 0.55 + b.seed, b.seed * 2.3, b.seed + 47);
          const crack = SCALE > 1 && b.sourceW > 5
            && materialDepth > b.sourceH * 0.2 && materialDepth < b.sourceH * 0.74
            && Math.abs(localX - crackX) < 0.27 && crackNoise > 0.32;
          if (crack) {
            const previousX = -b.sourceW * 0.2 + Math.sin((materialDepth - 0.5) * 0.7 + b.ph) * 0.15;
            glyph = crackX > previousX ? S.crackBackslash : S.crackSlash;
            color = KEYS[ICE + 1];
          }
          g.set(x, y, glyph, color);
        }

        // Pale shelf under the water and a broken, lightly refracted reflection.
        const shelf = Math.round(b.prof[i] * 0.5);
        for (let y = hz; y < Math.min(rows, hz + shelf); y++) {
          const sx = x / SCALE;
          const sy = y / SCALE;
          const refraction = noise2(x * 0.18, y * 0.25, b.seed + 59);
          const wob = Math.sin(sy * 2 + motionT * 2 + sx * 0.3) > 0.2 + (refraction - 0.5) * 0.06;
          const fineBreak = !wob && refraction > 0.985;
          g.set(x + (wob ? SCALE : fineBreak ? 1 : 0), y,
            fineBreak ? S.waterGlint : wob ? S.reflectionMid : S.reflectionLight, KEYS[SUB + (sy - SOURCE_HORIZON < 2 ? 1 : 0)]);
        }
        g.set(x, hz, S.iceSurface, KEYS[ICE + 8]);
      }
    }

    return g.frame();
  };
}
