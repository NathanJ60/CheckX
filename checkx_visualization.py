#!/usr/bin/env python3
"""checkx_visualization.py - Rendu PNG des puzzles Check X."""

from PIL import Image, ImageDraw, ImageFont
import os

from checkx_model import GRID

TARGET_PX = 2000

BG_COLOR = "#FFFFFF"
CELL_COLOR = "#FFFFFF"
BLACK_CELL_COLOR = "#000000"
BORDER_COLOR = "#000000"
TEXT_COLOR = "#000000"


def _load_font(size):
    for path in [
        "Arial Bold.ttf", "Arial-Bold.ttf", "ArialBd.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_checkx(puzzle, base_path="checkx_grid"):
    """Génère les images PNG puzzle + solution.

    Retourne [solution_path, puzzle_path].
    """
    solution = puzzle['solution']
    blacks = puzzle['blacks']
    hints = puzzle['hints']

    # Proportions
    margin_base = 10
    cell_base = 80
    total_base = margin_base * 2 + cell_base * GRID

    scale = TARGET_PX / total_base
    cell = int(cell_base * scale)
    margin = int(margin_base * scale)
    border_w = max(2, int(2.5 * scale))
    font_size = int(48 * scale)

    img_size = margin * 2 + cell * GRID
    font = _load_font(font_size)
    image_paths = []

    for label, show_all in [("solution", True), ("puzzle", False)]:
        path = f"{base_path}_{label}.png"
        img = Image.new("RGB", (img_size, img_size), BG_COLOR)
        draw = ImageDraw.Draw(img)

        def cell_topleft(r, c):
            return (margin + c * cell, margin + r * cell)

        # Cases
        for r in range(GRID):
            for c in range(GRID):
                x, y = cell_topleft(r, c)
                if blacks[r][c]:
                    draw.rectangle([x, y, x + cell, y + cell],
                                   fill=BLACK_CELL_COLOR, outline=BORDER_COLOR, width=border_w)
                else:
                    draw.rectangle([x, y, x + cell, y + cell],
                                   fill=CELL_COLOR, outline=BORDER_COLOR, width=border_w)
                    val = solution[r][c] if show_all else hints[r][c]
                    if val and val != 0:
                        text = str(val)
                        bbox = draw.textbbox((0, 0), text, font=font)
                        tw = bbox[2] - bbox[0]
                        th = bbox[3] - bbox[1]
                        tx = x + (cell - tw) // 2 - bbox[0]
                        ty = y + (cell - th) // 2 - bbox[1]
                        draw.text((tx, ty), text, fill=TEXT_COLOR, font=font)

        # Bordure extérieure
        draw.rectangle([(0, 0), (img_size - 1, img_size - 1)],
                       outline=BORDER_COLOR, width=max(2, int(3 * scale)))

        img.save(path)
        image_paths.append(path)
        print(f"Image '{label}' générée : {path}")

    return image_paths
