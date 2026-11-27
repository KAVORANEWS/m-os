#!/usr/bin/env python3
"""Generate the original M OS application icons as SVG.

All icons share one design language: a rounded "squircle" tile with an
M OS gradient and a white line glyph. Run this script after editing the
glyphs; scripts/render-branding.sh then rasterises them.
License: CC-BY-SA-4.0
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent / "scalable"

TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!-- M OS application icon: {name}. Original artwork. License: CC-BY-SA-4.0 -->
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{c1}"/>
      <stop offset="1" stop-color="{c2}"/>
    </linearGradient>
    <linearGradient id="gl" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.25"/>
      <stop offset="0.55" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect x="6" y="6" width="116" height="116" rx="28" fill="url(#bg)"/>
  <rect x="6" y="6" width="116" height="116" rx="28" fill="url(#gl)"/>
  <g fill="none" stroke="#FFFFFF" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
    {glyph}
  </g>
</svg>
"""

ICONS = {
    # The M OS mark itself
    "mos-logo": ("#6366F1", "#0EA5E9",
                 '<path d="M38 88 V42 L64 72 L90 42 V88"/>'),
    # Welcome: sparkle
    "mos-welcome": ("#8B5CF6", "#EC4899",
                    '<path d="M64 30 L71 57 L98 64 L71 71 L64 98 L57 71 L30 64 L57 57 Z"/>'
                    '<path d="M94 30 v12 M88 36 h12" stroke-width="5"/>'),
    # Control Center: sliders
    "mos-control-center": ("#475569", "#6366F1",
                           '<path d="M36 44 H92 M36 64 H92 M36 84 H92" stroke-opacity="0.55"/>'
                           '<circle cx="76" cy="44" r="8" fill="#FFFFFF"/>'
                           '<circle cx="52" cy="64" r="8" fill="#FFFFFF"/>'
                           '<circle cx="84" cy="84" r="8" fill="#FFFFFF"/>'),
    # Update Center: circular arrow + down arrow
    "mos-update-center": ("#10B981", "#0EA5E9",
                          '<path d="M92 60 A28 28 0 1 1 82 40"/>'
                          '<path d="M84 26 V42 H68"/>'
                          '<path d="M64 52 V76 M54 67 L64 77 L74 67" stroke-width="6"/>'),
    # System Monitor: pulse line
    "mos-system-monitor": ("#F59E0B", "#EF4444",
                           '<path d="M28 68 H46 L54 46 L66 88 L76 58 L82 68 H100"/>'),
    # About: info
    "mos-about": ("#3B82F6", "#7C3AED",
                  '<circle cx="64" cy="64" r="32"/>'
                  '<path d="M64 60 V82"/><circle cx="64" cy="47" r="3.5" fill="#FFFFFF"/>'),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (c1, c2, glyph) in ICONS.items():
        (OUT / f"{name}.svg").write_text(
            TEMPLATE.format(name=name, c1=c1, c2=c2, glyph=glyph), encoding="utf-8")
        print(f"wrote {name}.svg")


if __name__ == "__main__":
    main()
