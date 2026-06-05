"""Render the Fig. 4 cyclone-comparison share card -> web/public/og-image.png.

A 1200x630 raster of the "same low, two worlds" figure (CycloneCompare.tsx):
left panel f = 0 (inflow converges but never turns), right panel rotating Earth
(the identical inflow winds into a spiral). Reproduces the figure's static
streamline geometry, then frames it as a social card.

Run with the model venv (Pillow + NumPy):

    model/.venv/bin/python web/scripts/og-fig4.py

The output (og-image.png) is committed and shipped; regenerate only if the
figure or copy changes. Uses macOS system fonts (Menlo + Baskerville).
"""

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = "/Users/ericruzanski/Developer/planeoldweather"
BASK = "/System/Library/Fonts/Supplemental/Baskerville.ttc"  # 4 = SemiBold
MENLO = "/System/Library/Fonts/Menlo.ttc"
S = 2  # supersample, then LANCZOS down for clean AA

W, H = 1200, 630
w, hh = W * S, H * S

INK = (8, 10, 20)
PARCH = (236, 227, 208)
PARCH_DIM = (185, 176, 160)
PARCH_FAINT = (138, 132, 114)
AMBER = (240, 169, 76)
COOL = (132, 169, 204)  # f = 0 panel
WARM = (240, 169, 76)  # rotating panel


def menlo(px):
    return ImageFont.truetype(MENLO, round(px))


def bask(px, index=4):
    return ImageFont.truetype(BASK, round(px), index=index)


# --- background: ink + a faint center-lifting vignette ---
yy, xx = np.mgrid[0:hh, 0:w].astype(np.float32)
base = np.empty((hh, w, 3), np.float32)
base[:] = INK
vig = np.clip(1 - np.hypot(xx - w / 2, yy - hh * 0.52) / (w * 0.62), 0, 1) ** 2
base += vig[..., None] * np.array((22, 28, 46)) * 0.5
img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
dr = ImageDraw.Draw(img, "RGBA")

# --- figure geometry (mirrors CycloneCompare.tsx) ---
cy = hh * 0.54
centers = (w * 0.27, w * 0.73)
maxR = min(w * 0.19, hh * 0.4)
N = 18  # streamlines per panel (a touch denser than the live fig, for a thumbnail)


def streamline(cx, a0, spiral):
    pts = []
    r = maxR
    while r > 5 * S:
        t = 1 - r / maxR
        ang = a0 + t * 4.6 if spiral else a0
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        r -= 2 * S
    return pts


for panel, cx in enumerate(centers):
    color = (COOL if panel == 0 else WARM) + (panel == 0 and 150 or 165,)
    for k in range(N):
        a0 = k / N * math.tau
        dr.line(streamline(cx, a0, spiral=panel == 1), fill=color, width=round(1.7 * S), joint="curve")

# center markers with a soft amber glow
for cx in centers:
    for rr, a in ((16 * S, 60), (9 * S, 120)):
        dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=AMBER + (a,))
    dr.ellipse([cx - 5 * S, cy - 5 * S, cx + 5 * S, cy + 5 * S], fill=AMBER + (255,))

# divider
dr.line([w / 2, hh * 0.16, w / 2, hh * 0.9], fill=PARCH + (26,), width=S)


def centered(text, font, cx, y, fill):
    tw = dr.textlength(text, font=font)
    dr.text((cx - tw / 2, y), text, font=font, fill=fill)


# --- framing copy ---
centered("Plane Old Weather", bask(52 * S), w / 2, 40 * S, PARCH)
centered("THE CORIOLIS TEST — THE SAME LOW, TWO WORLDS", menlo(17 * S), w / 2, 110 * S, AMBER + (255,))

tag = menlo(18 * S)
centered("f = 0 · converges, never turns", tag, centers[0], 168 * S, COOL + (255,))
centered("rotating · winds into a spiral", tag, centers[1], 168 * S, WARM + (255,))

centered("planeoldweather.com", menlo(18 * S), w / 2, 566 * S, PARCH_FAINT + (255,))

out = f"{ROOT}/web/public/og-image.png"
img.resize((W, H), Image.LANCZOS).save(out, optimize=True)
print("wrote", out, (W, H))
