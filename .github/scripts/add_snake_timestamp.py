#!/usr/bin/env python3
"""Stamp an 'Updated: <UTC time>' footer onto the snake SVG, matching the stats card style."""
import re
import sys
from datetime import datetime, timezone

FOOTER_H = 20


def add_timestamp(path):
    with open(path, 'r', encoding='utf-8') as f:
        svg = f.read()

    tag_match = re.search(r'<svg\b[^>]*>', svg)
    tag = tag_match.group(0)

    height_match = re.search(r'height="([\d.]+)"', tag)
    height = float(height_match.group(1))
    new_height = height + FOOTER_H
    new_tag = tag[:height_match.start(1)] + f'{new_height:g}' + tag[height_match.end(1):]

    # Text coordinates live in the viewBox's user space, which may be offset
    # from (0,0) — Platane/snk emits e.g. viewBox="-16 -32 880 192". Anchor
    # the footer relative to that origin, not the raw width/height attrs.
    vb_match = re.search(r'viewBox="([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+)"', new_tag)
    if vb_match:
        vb_x, vb_y, vb_w, vb_h = (float(v) for v in vb_match.groups())
        new_vb = f'viewBox="{vb_x:g} {vb_y:g} {vb_w:g} {vb_h + FOOTER_H:g}"'
        new_tag = new_tag[:vb_match.start()] + new_vb + new_tag[vb_match.end():]
        center_x = vb_x + vb_w / 2
        text_y = vb_y + vb_h + 14
    else:
        width = float(re.search(r'width="([\d.]+)"', tag).group(1))
        center_x = width / 2
        text_y = height + 14

    svg = svg[:tag_match.start()] + new_tag + svg[tag_match.end():]

    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    text_el = (
        f'<text x="{center_x:g}" y="{text_y:g}" '
        'font-family="Segoe UI, Ubuntu, sans-serif" font-size="11" '
        f'fill="#888888" text-anchor="middle">Updated: {timestamp}</text>'
    )
    svg = svg.replace('</svg>', text_el + '</svg>', 1)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(svg)


if __name__ == '__main__':
    for svg_path in sys.argv[1:]:
        add_timestamp(svg_path)
        print(f"Stamped {svg_path}")
