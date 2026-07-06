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

    width = float(re.search(r'width="([\d.]+)"', tag).group(1))
    height = float(re.search(r'height="([\d.]+)"', tag).group(1))
    new_height = height + FOOTER_H

    new_tag = re.sub(r'height="[\d.]+"', f'height="{new_height:g}"', tag, count=1)

    vb_match = re.search(r'viewBox="([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+)"', new_tag)
    if vb_match:
        vb_x, vb_y, vb_w, vb_h = vb_match.groups()
        new_vb = f'viewBox="{vb_x} {vb_y} {vb_w} {float(vb_h) + FOOTER_H:g}"'
        new_tag = new_tag[:vb_match.start()] + new_vb + new_tag[vb_match.end():]

    svg = svg[:tag_match.start()] + new_tag + svg[tag_match.end():]

    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    text_el = (
        f'<text x="{width / 2:g}" y="{height + 14:g}" '
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
