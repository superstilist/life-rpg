"""Tests for the ascii_sr engine."""

from __future__ import annotations

import numpy as np
import pytest

from ascii_sr import SRConfig, read_frames, SuperResolver
from ascii_sr.config import CHARSETS
from ascii_sr.frames import Frame, parse_ansi, format_ansi, apply_timing
from ascii_sr.sdf import signed_distance, contour_from_sdf, gradient_magnitude
from ascii_sr.flow import estimate_flow, flow_magnitude, warp, temporal_denoise, warp_index_grid
from ascii_sr.metrics import psnr, ssim
from ascii_sr.rasterize import FrameRasterizer
from ascii_sr.glyphs import build_atlas, GlyphRenderer
from ascii_sr.match import match_cells, patch_features
from ascii_sr.demo import render_demo
from ascii_sr.cnn import HAS_TORCH, CNNRefiner


def _cfg(**kw):
    merged = {"quality": "fast", "cnn": "off"}
    merged.update(kw)
    if "scale" not in merged:
        merged["scale"] = 2
    if "charset" not in merged:
        merged["charset"] = "auto"
    return SRConfig.with_preset(**merged)


# ---------------------------------------------------------------------------
# ANSI round-trip
# ---------------------------------------------------------------------------


def test_ansi_roundtrip():
    rows = ["AB", "CD"]
    colors = np.array([[[10, 20, 30], [40, 50, 60]], [[70, 80, 90], [100, 110, 120]]], dtype=np.uint8)
    frame = Frame(rows, colors)
    text = frame.ansi()
    parsed = parse_ansi(text)
    assert parsed.rows == rows
    assert parsed.colors is not None
    np.testing.assert_array_equal(parsed.colors, colors)


def test_ansi_plain_no_color():
    rows = ["hello"]
    frame = Frame(rows, None)
    assert frame.has_color is False
    parsed = parse_ansi("hello")
    assert parsed.rows == rows
    assert parsed.colors is None


def test_format_ansi_roundtrip():
    rows = ["X"]
    colors = np.array([[[5, 6, 7]]], dtype=np.uint8)
    s = format_ansi(rows, colors)
    p = parse_ansi(s)
    assert p.rows == rows
    np.testing.assert_array_equal(p.colors, colors)


# ---------------------------------------------------------------------------
# Dimension scaling
# ---------------------------------------------------------------------------


def test_dimension_scaling():
    frames = render_demo(8, 4, 2, 12.0)
    for scale in (2, 4, 8):
        cfg = SRConfig.with_preset(quality="fast", scale=scale, charset="blocks", cnn="off")
        resolver = SuperResolver(cfg)
        result = resolver.run(frames)
        assert len(result.frames) == len(frames)
        out_w = 8 * scale
        out_h = 4 * scale
        for f in result.frames:
            assert len(f.rows) == out_h
            assert all(len(r) == out_w for r in f.rows)
            assert f.indices.shape == (out_h, out_w)


# ---------------------------------------------------------------------------
# Timing preservation
# ---------------------------------------------------------------------------


def test_timing_preservation():
    frames = render_demo(8, 4, 3, 12.0)
    cfg = _cfg()
    resolver = SuperResolver(cfg)
    result = resolver.run(frames)
    assert len(result.durations) == len(frames)
    # input timing 1000/12 ms each
    for d in result.durations:
        assert abs(d - (1000.0 / 12.0)) < 1e-6
    assert abs(result.fps - 12.0) < 1e-6


def test_apply_timing_fallback():
    frames = [Frame(["ab"], None) for _ in range(2)]
    d = apply_timing(frames, 10.0)
    assert d == [100.0, 100.0]


# ---------------------------------------------------------------------------
# Flow: static and translation
# ---------------------------------------------------------------------------


def test_flow_static():
    img = np.random.default_rng(0).random((32, 32)).astype(np.float32)
    flow = estimate_flow(img, img, levels=2)
    assert flow.shape == (2, 32, 32)
    # static scene -> near-zero flow
    assert flow_magnitude(flow) < 0.5


def test_flow_translation():
    img = np.zeros((40, 40), np.float32)
    img[10:20, 10:20] = 1.0
    shifted = np.zeros((40, 40), np.float32)
    shifted[12:22, 13:23] = 1.0
    flow = estimate_flow(img, shifted, levels=2, search=6)
    # mean flow should be nonzero
    assert flow_magnitude(flow) > 0.5


def test_warp_roundtrip():
    img = np.arange(16, dtype=np.float32).reshape(4, 4)
    flow = np.zeros((2, 4, 4), np.float32)
    w = warp(img, flow)
    np.testing.assert_allclose(w, img, atol=1e-5)


def test_temporal_denoise_reduces():
    a = np.full((8, 8), 0.5, dtype=np.float32)
    b = np.full((8, 8), 0.5, dtype=np.float32)
    flow = np.zeros((2, 8, 8), dtype=np.float32)
    out = temporal_denoise(a, b, flow, strength=0.5)
    np.testing.assert_allclose(out, 0.5, atol=1e-6)


# ---------------------------------------------------------------------------
# SDF contour
# ---------------------------------------------------------------------------


def test_sdf_contour():
    mask = np.zeros((16, 16), np.float32)
    mask[4:12, 4:12] = 1.0
    sdf = signed_distance(mask, 0.5)
    # inside positive, outside negative
    assert sdf[8, 8] > 0
    assert sdf[0, 0] < 0
    # contour near zero on the edge
    c = contour_from_sdf(sdf, scale=2.0)
    assert c.shape == mask.shape
    assert 0.0 <= c.min() and c.max() <= 1.0
    # edge pixels have intermediate values
    edge_val = c[4, 8]
    assert 0.0 < edge_val < 1.0
    g = gradient_magnitude(mask)
    assert g.shape == mask.shape


def test_sdf_uniform():
    mask = np.ones((8, 8), np.float32)
    sdf = signed_distance(mask, 0.5)
    # all inside -> large positive
    assert np.all(sdf > 0)


# ---------------------------------------------------------------------------
# Glyph atlas / matching
# ---------------------------------------------------------------------------


def test_atlas_build():
    atlas = build_atlas("blocks", (8, 16), supersample=2, use_cache=True)
    assert atlas.size > 1
    assert atlas.masks.shape[1:] == (16, 8)
    assert atlas.uniformity.shape == (atlas.size,)
    assert " " in atlas.chars


def test_match_cells_shape():
    atlas = build_atlas("blocks", (8, 16), supersample=2, use_cache=True)
    patches = np.zeros((4, 16, 8), np.float32)
    patches[0, 2:14, 2:6] = 1.0
    cfg = _cfg()
    out = match_cells(patches, atlas, cfg)
    assert out.shape == (4,)
    assert out.dtype == np.int32


def test_patch_features():
    patches = np.zeros((2, 16, 8), np.float32)
    f = patch_features(patches, (8, 16))
    assert f["coarse"].shape[0] == 2
    assert f["uniformity"].shape == (2,)


# ---------------------------------------------------------------------------
# Hysteresis reduction (flicker)
# ---------------------------------------------------------------------------


def test_hysteresis_keeps():
    frames = render_demo(8, 4, 4, 12.0)
    cfg = _cfg(hysteresis=0.5)
    resolver = SuperResolver(cfg)
    result = resolver.run(frames)
    retentions = [f.retained for f in result.frames[1:]]
    # hysteresis should keep a large fraction of cells on a smooth clip
    assert np.mean(retentions) > 0.5


# ---------------------------------------------------------------------------
# CNN smoke
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_TORCH, reason="torch not available")
def test_cnn_smoke():
    cfg = SRConfig.with_preset(quality="fast", scale=2, charset="blocks", cnn="on", cnn_steps=3, cnn_channels=8)
    cnn = CNNRefiner(cfg)
    a = np.random.default_rng(1).random((32, 32)).astype(np.float32)
    b = np.random.default_rng(2).random((32, 32)).astype(np.float32)
    cnn.fit([(a, b)])
    assert cnn.trained is True
    out = cnn.apply(a)
    assert out.shape == a.shape
    assert np.isfinite(out).all()


# ---------------------------------------------------------------------------
# Full demo run (small)
# ---------------------------------------------------------------------------


def test_demo_run():
    frames = render_demo(12, 6, 3, 12.0)
    cfg = _cfg(charset="auto")
    resolver = SuperResolver(cfg)
    result = resolver.run(frames)
    manifest_dir = None
    import tempfile, os
    d = tempfile.mkdtemp()
    result.write(d)
    assert (os.path.join(d, "manifest.json"))
    import json
    m = json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8"))
    assert m["metrics"]["psnr_mean"] > 0
    assert m["metrics"]["flicker_mean"] >= 0
    assert os.path.exists(os.path.join(d, "preview.gif"))


# ---------------------------------------------------------------------------
# Rasterizer
# ---------------------------------------------------------------------------


def test_rasterizer_luma():
    atlas = build_atlas("blocks", (8, 16), supersample=2, use_cache=True)
    renderer = GlyphRenderer(atlas.font, (8, 16), supersample=2)
    r = FrameRasterizer(renderer, (8, 16))
    out = r.luma(["AB", "CD"], None)
    assert out.shape == (32, 16)


def test_color_luminance():
    from ascii_sr.rasterize import color_luminance
    c = np.zeros((2, 2, 3), dtype=np.uint8)
    c[..., 0] = 255
    out = color_luminance(c, 2, 2)
    assert out.shape == (2, 2)
    assert out.min() >= 0.02


# ---------------------------------------------------------------------------
# Read frames from dir
# ---------------------------------------------------------------------------


def test_read_frames_roundtrip_tmp(tmp_path):
    frames = render_demo(6, 3, 2, 10.0)
    from ascii_sr.frames import write_frames
    durations = [f.duration_ms for f in frames]
    write_frames(tmp_path, frames, durations, ansi="never")
    loaded = read_frames(tmp_path / "frames")
    assert len(loaded) == len(frames)
    assert loaded[0].width == frames[0].width
    assert loaded[0].height == frames[0].height


def test_read_single_file(tmp_path):
    frames = render_demo(6, 3, 2, 10.0)
    from ascii_sr.frames import write_frames
    durations = [f.duration_ms for f in frames]
    # write a single multi-frame file via form feed
    p = tmp_path / "clip.txt"
    text = "\x0c".join(f.text() for f in frames)
    p.write_text(text, encoding="utf-8")
    loaded = read_frames(p)
    assert len(loaded) == len(frames)
