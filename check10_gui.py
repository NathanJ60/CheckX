#!/usr/bin/env python3
"""check10_gui.py - Interface graphique complète Check 10.

Features: génération, difficulté, export PNG/SVG/PDF/XML, thèmes,
personnalisation des couleurs.
"""

import sys
import os
import shutil
import xml.etree.ElementTree as ET
import base64
from enum import Enum

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout,
    QHBoxLayout, QWidget, QLabel, QComboBox, QSizePolicy,
    QFileDialog, QMessageBox, QCheckBox,
    QColorDialog, QDialog, QGridLayout, QDialogButtonBox,
)
from PyQt5.QtGui import QPixmap, QFont, QColor
from PyQt5.QtCore import Qt

from check10_model import generate_puzzle, verify_puzzle, GRID
from check10_visualization import (
    draw_check10, draw_check10_svg, draw_check10_pdf,
    Theme, _THEME_STYLES, SVG_AVAILABLE, PDF_AVAILABLE,
)


class DifficultyLevel(Enum):
    FACILE = "facile"
    MOYEN = "moyen"
    DIFFICILE = "difficile"


class Check10App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Check 10 Generator")
        self.setMinimumSize(700, 800)
        self.resize(900, 1000)
        self.puzzle = None
        self.image_paths = []
        self.current_difficulty = DifficultyLevel.MOYEN
        self.save_counter = 1
        self.init_ui()

    # -------------------- UI --------------------
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        title = QLabel("Générateur Check 10")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Difficulté
        diff_layout = QHBoxLayout()
        diff_layout.addWidget(QLabel("Difficulté :"))
        self.diff_combo = QComboBox()
        for lvl in DifficultyLevel:
            self.diff_combo.addItem(lvl.value.capitalize(), lvl)
        self.diff_combo.setCurrentText(DifficultyLevel.MOYEN.value.capitalize())
        self.diff_combo.currentIndexChanged.connect(self.on_difficulty_changed)
        diff_layout.addWidget(self.diff_combo)
        diff_layout.addStretch()
        layout.addLayout(diff_layout)

        # Bouton génération
        gen_btn = QPushButton("Générer un puzzle")
        gen_btn.clicked.connect(self.generate_new_puzzle)
        layout.addWidget(gen_btn)

        # Boutons export
        save_layout = QHBoxLayout()
        save_png = QPushButton("Enregistrer (PNG)")
        save_png.clicked.connect(self.save_grid_png)
        save_layout.addWidget(save_png)

        save_svg = QPushButton("Enregistrer (SVG)")
        save_svg.clicked.connect(self.save_grid_svg)
        save_svg.setEnabled(SVG_AVAILABLE)
        save_layout.addWidget(save_svg)

        save_pdf = QPushButton("Enregistrer (PDF)")
        save_pdf.clicked.connect(self.save_grid_pdf)
        save_pdf.setEnabled(PDF_AVAILABLE)
        save_layout.addWidget(save_pdf)
        layout.addLayout(save_layout)

        # XML + color customizer
        export_layout = QHBoxLayout()
        xml_btn = QPushButton("Exporter en XML")
        xml_btn.clicked.connect(self.export_xml)
        export_layout.addWidget(xml_btn)
        self.include_images_cb = QCheckBox("Inclure les images")
        self.include_images_cb.setChecked(True)
        export_layout.addWidget(self.include_images_cb)
        color_btn = QPushButton("Personnaliser couleurs…")
        color_btn.clicked.connect(self.open_color_customizer)
        export_layout.addWidget(color_btn)
        layout.addLayout(export_layout)

        # Thème
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Thème :"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Classique", "Sombre", "Pastel"])
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)

        # Affichage des images
        images_layout = QHBoxLayout()
        self.grid_label = QLabel("Générez un puzzle pour commencer")
        self.solution_label = QLabel("")
        for lbl in (self.grid_label, self.solution_label):
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setMinimumSize(100, 100)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            lbl.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
            images_layout.addWidget(lbl, 1)
        layout.addLayout(images_layout)

    # -------------------- Helpers --------------------
    def on_difficulty_changed(self):
        self.current_difficulty = self.diff_combo.itemData(self.diff_combo.currentIndex())

    def on_theme_changed(self):
        if self.puzzle:
            temp = "temp_check10"
            os.makedirs(temp, exist_ok=True)
            self.image_paths = draw_check10(
                self.puzzle, os.path.join(temp, "check10"), theme=self._selected_theme()
            )
            self._update_display()

    def _selected_theme(self):
        return [Theme.CLASSIC, Theme.DARK, Theme.PASTEL][self.theme_combo.currentIndex()]

    # -------------------- Génération --------------------
    def generate_new_puzzle(self):
        self.solution_label.setText("Génération...")
        self.grid_label.setText("")
        QApplication.processEvents()

        try:
            puzzle = generate_puzzle(self.current_difficulty.value)
            if not puzzle:
                QMessageBox.critical(self, "Échec", "Impossible de générer un puzzle.")
                self.solution_label.setText("Échec")
                return

            self.puzzle = puzzle
            verify_puzzle(puzzle)

            temp = "temp_check10"
            os.makedirs(temp, exist_ok=True)
            self.image_paths = draw_check10(
                puzzle, os.path.join(temp, "check10"), theme=self._selected_theme()
            )
            self._update_display()
        except Exception as e:
            self.solution_label.setText(f"Erreur : {e}")
            import traceback
            traceback.print_exc()

    def _update_display(self):
        if not self.image_paths:
            return
        # image_paths[0] = solution, [1] = puzzle
        for path, label in zip(self.image_paths, [self.solution_label, self.grid_label]):
            pix = QPixmap(path)
            side = min(max(50, label.width() - 20), max(50, label.height() - 20))
            label.setPixmap(pix.scaled(side, side, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    # -------------------- Export --------------------
    def save_grid_png(self):
        self._save_format("PNG", ".png", draw_check10)

    def save_grid_svg(self):
        self._save_format("SVG", ".svg", draw_check10_svg)

    def save_grid_pdf(self):
        self._save_format("PDF", ".pdf", draw_check10_pdf)

    def _save_format(self, fmt, ext, draw_fn):
        if not self.puzzle:
            QMessageBox.warning(self, "Attention", "Aucun puzzle généré.")
            return
        save_dir = QFileDialog.getExistingDirectory(self, f"Dossier {fmt}", os.path.expanduser("~"))
        if not save_dir:
            return
        try:
            while True:
                p = os.path.join(save_dir, f"Check10_{self.save_counter}{ext}")
                s = os.path.join(save_dir, f"Check10_{self.save_counter}_solution{ext}")
                if not os.path.exists(p) and not os.path.exists(s):
                    break
                self.save_counter += 1
            n = self.save_counter
            temp = "temp_check10"
            os.makedirs(temp, exist_ok=True)
            paths = draw_fn(self.puzzle, os.path.join(temp, f"check10_{n}"),
                            theme=self._selected_theme())
            for img in paths:
                suffix = "_solution" if "solution" in img else ""
                shutil.copy2(img, os.path.join(save_dir, f"Check10_{n}{suffix}{ext}"))
            self.save_counter += 1
            QMessageBox.information(self, "OK", f"Sauvegardé dans {save_dir}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def export_xml(self):
        if not self.puzzle:
            QMessageBox.warning(self, "Attention", "Aucun puzzle généré.")
            return
        save_dir = QFileDialog.getExistingDirectory(self, "Dossier XML", os.path.expanduser("~"))
        if not save_dir:
            return
        try:
            while True:
                fp = os.path.join(save_dir, f"check10_{self.save_counter}.xml")
                if not os.path.exists(fp):
                    break
                self.save_counter += 1

            p = self.puzzle
            root = ET.Element("check10", rows=str(GRID), cols=str(GRID),
                              difficulty=p.get('difficulty', ''),
                              num_blacks=str(p.get('num_blacks', 0)),
                              num_hints=str(p.get('num_hints', 0)))

            # Solution
            sol_el = ET.SubElement(root, "solution")
            for r in range(GRID):
                for c in range(GRID):
                    attrs = {"r": str(r), "c": str(c)}
                    if p['blacks'][r][c]:
                        attrs["value"] = "black"
                    else:
                        attrs["value"] = str(p['solution'][r][c])
                    ET.SubElement(sol_el, "cell", attrs)

            # Puzzle (indices)
            puz_el = ET.SubElement(root, "puzzle")
            for r in range(GRID):
                for c in range(GRID):
                    attrs = {"r": str(r), "c": str(c)}
                    if p['blacks'][r][c]:
                        attrs["value"] = "black"
                    elif p['hints'][r][c] != 0:
                        attrs["value"] = str(p['hints'][r][c])
                    else:
                        attrs["value"] = ""
                    ET.SubElement(puz_el, "cell", attrs)

            # Images base64
            if self.include_images_cb.isChecked() and self.image_paths:
                imgs_el = ET.SubElement(root, "images")
                for img_path in self.image_paths:
                    if os.path.exists(img_path):
                        name = "solution" if "solution" in img_path else "puzzle"
                        with open(img_path, "rb") as f:
                            ET.SubElement(imgs_el, "image", {"type": name}).text = \
                                base64.b64encode(f.read()).decode()

            ET.ElementTree(root).write(fp, encoding="utf-8", xml_declaration=True)
            self.save_counter += 1
            QMessageBox.information(self, "OK", f"Exporté : {fp}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    # -------------------- Personnalisation couleurs --------------------
    def open_color_customizer(self):
        theme = self._selected_theme()
        palette = _THEME_STYLES[theme]

        dlg = QDialog(self)
        dlg.setWindowTitle("Personnaliser les couleurs")
        layout = QGridLayout(dlg)

        color_items = [
            ("bg", "Fond extérieur"),
            ("cell", "Case blanche"),
            ("black_cell", "Case noire"),
            ("border", "Bordure"),
            ("text", "Texte (chiffres)"),
        ]

        for row, (key, label) in enumerate(color_items):
            lbl = QLabel(label)
            btn = QPushButton()
            btn.setFixedWidth(80)
            initial = palette.get(key, "#FFFFFF")
            btn.setStyleSheet(f"background-color: {initial}")

            def make_handler(k=key, b=btn, p=palette):
                def _pick():
                    init = p.get(k, "#FFFFFF")
                    col = QColorDialog.getColor(QColor(init), self, "Choisir la couleur")
                    if col.isValid():
                        hex_col = col.name()
                        b.setStyleSheet(f"background-color: {hex_col}")
                        p[k] = hex_col
                return _pick
            btn.clicked.connect(make_handler())
            layout.addWidget(lbl, row, 0)
            layout.addWidget(btn, row, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        layout.addWidget(bb, len(color_items), 0, 1, 2)

        if dlg.exec_() == QDialog.Accepted and self.puzzle:
            temp = "temp_check10"
            os.makedirs(temp, exist_ok=True)
            self.image_paths = draw_check10(
                self.puzzle, os.path.join(temp, "check10"), theme=theme
            )
            self._update_display()

    # -------------------- Resize --------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.image_paths:
            self._update_display()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Check10App()
    window.show()
    sys.exit(app.exec_())
