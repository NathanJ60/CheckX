#!/usr/bin/env python3
"""Génère des grilles Check 10 par niveau et écrit les PNG dans output/."""

import os
import sys
import time

from check10_model import (
    generate_puzzle, verify_puzzle, _max_2_blacks_per_row_col,
    _max_hints_per_segment, GRID,
)
from check10_visualization import draw_check10


def run(n_per_level: int = 5, out_dir: str = "output"):
    os.makedirs(out_dir, exist_ok=True)
    total_start = time.time()
    results = []

    for difficulty in ("difficile", "moyen", "facile"):
        print(f"\n=== Niveau {difficulty} : {n_per_level} grilles ===")
        for i in range(n_per_level):
            t0 = time.time()
            p = generate_puzzle(difficulty, enforce_unique_history=True)
            dt = time.time() - t0
            if p is None:
                print(f"  [{i+1:02d}] ECHEC: Echec ({dt:.1f}s)")
                continue

            valid = verify_puzzle(p)
            max2_ok = _max_2_blacks_per_row_col(p["blacks"])
            # Aucun indice sur segment de longueur 2
            len2_hints = 0
            for seg in p["segments"]:
                if len(seg) == 2:
                    len2_hints += sum(1 for (r, c) in seg if p["hints"][r][c] != 0)

            base = os.path.join(out_dir, f"Check10_{difficulty}_{i+1:02d}")
            draw_check10(p, base)

            status = "OK:" if (valid and max2_ok and len2_hints == 0) else "ECHEC:"
            print(f"  [{i+1:02d}] {status} noires={p['num_blacks']} indices={p['num_hints']} "
                  f"max2={max2_ok} len2_hints={len2_hints} ({dt:.1f}s)")
            results.append({
                "difficulty": difficulty,
                "idx": i + 1,
                "valid": valid,
                "max2": max2_ok,
                "len2_hints": len2_hints,
            })

    total_dt = time.time() - total_start
    valid_count = sum(1 for r in results if r["valid"] and r["max2"] and r["len2_hints"] == 0)
    print(f"\n=== BILAN : {valid_count}/{len(results)} valides en {total_dt:.1f}s ===")
    print(f"  Fichiers dans {out_dir}/")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run(n_per_level=n)
