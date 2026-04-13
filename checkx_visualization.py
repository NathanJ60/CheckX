#!/usr/bin/env python3
"""checkx_visualization.py - Rendu des puzzles Check X (PNG/SVG/PDF)."""

from PIL import Image, ImageDraw, ImageFont
from enum import Enum
import os

from checkx_model import GRID

try:
    import svgwrite
    SVG_AVAILABLE = True
except ImportError:
    SVG_AVAILABLE = False

try:
    from reportlab.pdfgen import canvas as _pdf_canvas
    from reportlab.lib.colors import HexColor
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class Theme(Enum):
    CLASSIC = "classic"
    DARK = "dark"
    PASTEL = "pastel"


_THEME_STYLES = {
    Theme.CLASSIC: {
        "bg":        "#FFFFFF",   # Fond extérieur
        "cell":      "#FFFFFF",   # Case blanche
        "black_cell": "#000000",  # Case noire
        "border":    "#000000",   # Bordure
        "text":      "#000000",   # Chiffres
    },
    Theme.DARK: {
        "bg":        "#1a1a1a",
        "cell":      "#2a2a2a",
        "black_cell": "#E0E0E0",
        "border":    "#FFFFFF",
        "text":      "#FFFFFF",
    },
    Theme.PASTEL: {
        "bg":        "#FFF8F0",
        "cell":      "#FFFDF7",
        "black_cell": "#5D4037",
        "border":    "#8B4513",
        "text":      "#3E2723",
    },
}


def _get_palette(theme):
    if not isinstance(theme, Theme):
        try:
            theme = Theme(theme)
        except Exception:
            theme = Theme.CLASSIC
    return _THEME_STYLES.get(theme, _THEME_STYLES[Theme.CLASSIC])


TARGET_PX = 2000
BASE_MARGIN = 10
BASE_CELL = 80
BASE_FONT = 48


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


# =============================================================================
# PNG
# =============================================================================

def draw_checkx(puzzle, base_path="checkx_grid", theme=Theme.CLASSIC):
    """Génère les images PNG (solution + puzzle).

    Retourne [solution_path, puzzle_path].
    """
    palette = _get_palette(theme)
    solution = puzzle['solution']
    blacks = puzzle['blacks']
    hints = puzzle['hints']

    total_base = BASE_MARGIN * 2 + BASE_CELL * GRID
    scale = TARGET_PX / total_base
    cell = int(BASE_CELL * scale)
    margin = int(BASE_MARGIN * scale)
    border_w = max(2, int(2.5 * scale))
    font_size = int(BASE_FONT * scale)
    img_size = margin * 2 + cell * GRID

    font = _load_font(font_size)
    image_paths = []

    for label, show_all in [("solution", True), ("puzzle", False)]:
        path = f"{base_path}_{label}.png"
        img = Image.new("RGB", (img_size, img_size), palette["bg"])
        draw = ImageDraw.Draw(img)

        for r in range(GRID):
            for c in range(GRID):
                x = margin + c * cell
                y = margin + r * cell
                if blacks[r][c]:
                    draw.rectangle([x, y, x + cell, y + cell],
                                   fill=palette["black_cell"], outline=palette["border"], width=border_w)
                else:
                    draw.rectangle([x, y, x + cell, y + cell],
                                   fill=palette["cell"], outline=palette["border"], width=border_w)
                    val = solution[r][c] if show_all else hints[r][c]
                    if val and val != 0:
                        text = str(val)
                        bbox = draw.textbbox((0, 0), text, font=font)
                        tw = bbox[2] - bbox[0]
                        th = bbox[3] - bbox[1]
                        tx = x + (cell - tw) // 2 - bbox[0]
                        ty = y + (cell - th) // 2 - bbox[1]
                        draw.text((tx, ty), text, fill=palette["text"], font=font)

        # Bordure extérieure
        draw.rectangle([(0, 0), (img_size - 1, img_size - 1)],
                       outline=palette["border"], width=max(2, int(3 * scale)))

        img.save(path)
        image_paths.append(path)
        print(f"Image '{label}' générée : {path}")

    return image_paths


# =============================================================================
# SVG
# =============================================================================

def draw_checkx_svg(puzzle, base_path="checkx_grid", theme=Theme.CLASSIC):
    if not SVG_AVAILABLE:
        raise ImportError("svgwrite non installé")
    palette = _get_palette(theme)
    solution = puzzle['solution']
    blacks = puzzle['blacks']
    hints = puzzle['hints']

    cell = BASE_CELL
    margin = BASE_MARGIN
    size = margin * 2 + cell * GRID
    font_size = BASE_FONT

    image_paths = []
    for label, show_all in [("solution", True), ("puzzle", False)]:
        path = f"{base_path}_{label}.svg"
        dwg = svgwrite.Drawing(path, size=(f'{size}px', f'{size}px'))
        dwg.add(dwg.rect(insert=(0, 0), size=(size, size), fill=palette["bg"]))

        for r in range(GRID):
            for c in range(GRID):
                x = margin + c * cell
                y = margin + r * cell
                fill = palette["black_cell"] if blacks[r][c] else palette["cell"]
                dwg.add(dwg.rect(insert=(x, y), size=(cell, cell),
                                 fill=fill, stroke=palette["border"], stroke_width=3))
                if not blacks[r][c]:
                    val = solution[r][c] if show_all else hints[r][c]
                    if val and val != 0:
                        dwg.add(dwg.text(
                            str(val),
                            insert=(x + cell / 2, y + cell / 2 + font_size / 3),
                            text_anchor="middle",
                            font_family="Helvetica, Arial, sans-serif",
                            font_size=f"{font_size}px",
                            font_weight="bold",
                            fill=palette["text"],
                        ))

        # Bordure extérieure
        dwg.add(dwg.rect(insert=(0, 0), size=(size - 1, size - 1),
                         fill="none", stroke=palette["border"], stroke_width=5))
        dwg.save()
        image_paths.append(path)
        print(f"SVG '{label}' généré : {path}")

    return image_paths


# =============================================================================
# PDF
# =============================================================================

def draw_checkx_pdf(puzzle, base_path="checkx_grid", theme=Theme.CLASSIC):
    if not PDF_AVAILABLE:
        raise ImportError("reportlab non installé")
    palette = _get_palette(theme)
    solution = puzzle['solution']
    blacks = puzzle['blacks']
    hints = puzzle['hints']

    # Taille cible ~10 cm
    target_size = 10 * 28.35  # cm → pt
    pdf_scale = target_size / (BASE_MARGIN * 2 + BASE_CELL * GRID)
    cell = BASE_CELL * pdf_scale
    margin = BASE_MARGIN * pdf_scale
    font_size = BASE_FONT * pdf_scale
    size = target_size

    image_paths = []
    for label, show_all in [("solution", True), ("puzzle", False)]:
        path = f"{base_path}_{label}.pdf"
        c = _pdf_canvas.Canvas(path, pagesize=(size, size))

        # Fond
        c.setFillColor(HexColor(palette["bg"]))
        c.rect(0, 0, size, size, fill=1, stroke=0)

        for ri in range(GRID):
            for ci in range(GRID):
                x = margin + ci * cell
                y = size - (margin + (ri + 1) * cell)
                fill = palette["black_cell"] if blacks[ri][ci] else palette["cell"]
                c.setFillColor(HexColor(fill))
                c.setStrokeColor(HexColor(palette["border"]))
                c.setLineWidth(2 * pdf_scale)
                c.rect(x, y, cell, cell, fill=1, stroke=1)

                if not blacks[ri][ci]:
                    val = solution[ri][ci] if show_all else hints[ri][ci]
                    if val and val != 0:
                        t = str(val)
                        c.setFillColor(HexColor(palette["text"]))
                        c.setFont("Helvetica-Bold", font_size)
                        tw = c.stringWidth(t, "Helvetica-Bold", font_size)
                        c.drawString(x + (cell - tw) / 2, y + cell / 2 - font_size / 3, t)

        # Bordure extérieure
        c.setStrokeColor(HexColor(palette["border"]))
        c.setLineWidth(5 * pdf_scale)
        c.rect(0, 0, size, size, fill=0, stroke=1)

        c.save()
        image_paths.append(path)
        print(f"PDF '{label}' généré : {path}")

    return image_paths
