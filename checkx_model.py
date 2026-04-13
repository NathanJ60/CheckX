#!/usr/bin/env python3
"""checkx_model.py - Générateur de puzzles Check X.

Règles:
- Grille 8×8, cases blanches à remplir avec 1..6, cases noires = séparateurs.
- Tout segment (horizontal ou vertical) de ≥2 cases blanches entre deux bords
  ou cases noires doit avoir une somme égale à 10.
- Les segments de 1 case sont autorisés et sans contrainte.

Contraintes de génération:
- Entre 10 et 12 cases noires par grille.
- Les cases BLANCHES doivent rester 4-connectées (pas de région isolée).
- Au moins 1 case noire par ligne ET par colonne (limite longueur segment à 7).
- Sur un segment, pas plus de floor(len/2) indices (évite 3 indices sur 4).
"""

import random
from collections import deque
from itertools import product
from typing import List, Tuple, Optional

from checkx_model_history import is_unique as hist_unique, add_to_history

GRID = 8
TARGET_SUM = 10
DIGITS = (1, 2, 3, 4, 5, 6)

DIFFICULTY_HINTS = {
    "difficile": (10, 13),
    "moyen": (12, 15),
    "facile": (14, 17),
}


# =============================================================================
# Tuples valides par longueur de segment (précalculés)
# =============================================================================

def _enum_tuples(length: int, target: int = TARGET_SUM) -> List[Tuple[int, ...]]:
    """Tous les tuples de `length` chiffres (1..6) sommant à `target`."""
    result = []

    def rec(idx, acc, rem):
        if idx == length - 1:
            if 1 <= rem <= 6:
                result.append(tuple(acc + (rem,)))
            return
        remaining_cells = length - idx - 1
        min_remain_after = remaining_cells  # au minimum 1 par case restante
        max_remain_after = 6 * remaining_cells
        for d in DIGITS:
            r2 = rem - d
            if r2 < min_remain_after or r2 > max_remain_after:
                continue
            rec(idx + 1, acc + (d,), r2)

    rec(0, (), target)
    return result


_VALID_TUPLES = {n: _enum_tuples(n) for n in range(2, 9)}  # longueurs 2..8


# =============================================================================
# Pattern de cases noires
# =============================================================================

def _white_connected(blacks) -> bool:
    start = None
    total_white = 0
    for r in range(GRID):
        for c in range(GRID):
            if not blacks[r][c]:
                total_white += 1
                if start is None:
                    start = (r, c)
    if start is None:
        return False
    seen = {start}
    q = deque([start])
    while q:
        r, c = q.popleft()
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < GRID and 0 <= nc < GRID and not blacks[nr][nc] and (nr, nc) not in seen:
                seen.add((nr, nc))
                q.append((nr, nc))
    return len(seen) == total_white


# =============================================================================
# Templates connus faisables (dérivés du PDF officiel)
# =============================================================================

# Format compact: chaîne 64 chars, '.' = blanc, '#' = noir
# Templates tirés du PDF officiel (grilles connues faisables).
_TEMPLATE_PATTERNS = [
    # Template 1 : PDF top-right (11 noirs)
    (
        ".....#.#"
        "...#...."
        "........"
        ".#......"
        "......#."
        "#.#....#"
        "....#..."
        ".#.#...."
    ),
    # Template 2 : PDF bottom-right (13 noirs)
    (
        "....#..."
        "..#....#"
        "........"
        ".#...#.."
        "#..#..#."
        "..#....."
        ".#..#..."
        "...#...#"
    ),
]


def _parse_template(s: str) -> List[List[bool]]:
    rows = [s[i * GRID:(i + 1) * GRID] for i in range(GRID)]
    return [[ch == '#' for ch in row] for row in rows]


def _transform_pattern(blacks, rotation: int, flip_h: bool, flip_v: bool):
    """Applique rotation (0-3) et flips pour obtenir une variante."""
    result = [row[:] for row in blacks]
    # Flip horizontal
    if flip_h:
        result = [row[::-1] for row in result]
    # Flip vertical
    if flip_v:
        result = result[::-1]
    # Rotation 90° k fois
    for _ in range(rotation):
        result = [[result[GRID - 1 - c][r] for c in range(GRID)] for r in range(GRID)]
    return result


def _pick_template() -> List[List[bool]]:
    """Pioche un template au hasard et applique une transformation aléatoire."""
    s = random.choice(_TEMPLATE_PATTERNS)
    blacks = _parse_template(s)
    rot = random.randint(0, 3)
    fh = random.random() < 0.5
    fv = random.random() < 0.5
    return _transform_pattern(blacks, rot, fh, fv)


# Cache dynamique de patterns faisables découverts aléatoirement
_DYNAMIC_TEMPLATES = []


def _discover_random_feasible_pattern(max_tries: int = 50) -> Optional[List[List[bool]]]:
    """Génère des patterns aléatoires et retourne le premier qui est faisable
    (détecté via propagation rapide, sans solveur complet)."""
    for _ in range(max_tries):
        blacks = _random_pattern_strict()
        if blacks is None:
            continue
        segments, cell_to_segs = compute_segments(blacks)
        if not segments:
            continue
        if any(len(_VALID_TUPLES.get(len(s), [])) == 0 for s in segments):
            continue
        # Test rapide via propagation seule
        empty = [[0 if not blacks[r][c] else None for c in range(GRID)] for r in range(GRID)]
        domains, seg_tuples = _initial_domains(blacks, segments, cell_to_segs, empty)
        if _propagate(domains, segments, cell_to_segs, seg_tuples):
            # Propagation n'a pas détecté infaisabilité → probablement OK
            return blacks
    return None


def _random_pattern_strict(num_black_range=(10, 12)) -> Optional[List[List[bool]]]:
    """Génère un pattern aléatoire avec contraintes (connecté, row/col)."""
    lo, hi = num_black_range
    for _ in range(100):
        n = random.randint(lo, hi)
        blacks = [[False] * GRID for _ in range(GRID)]
        cells = [(r, c) for r in range(GRID) for c in range(GRID)]
        random.shuffle(cells)
        placed = 0
        for r, c in cells:
            if placed >= n:
                break
            blacks[r][c] = True
            if not _white_connected(blacks):
                blacks[r][c] = False
                continue
            placed += 1
        if placed == n and _each_row_col_has_black(blacks):
            return blacks
    return None


def _pick_pattern() -> List[List[bool]]:
    """Pioche un pattern: principalement via templates, parfois via fallback aléatoire."""
    # Avec probabilité 85% → templates (rapide, diversité via symétries+digits)
    # Sinon tenter d'étendre la bibliothèque avec un nouveau pattern aléatoire
    if random.random() < 0.85 or not _DYNAMIC_TEMPLATES:
        # Si on a des dynamiques, tirer parmi tous
        if _DYNAMIC_TEMPLATES and random.random() < 0.3:
            base = random.choice(_DYNAMIC_TEMPLATES)
        else:
            s = random.choice(_TEMPLATE_PATTERNS)
            base = _parse_template(s)
        rot = random.randint(0, 3)
        fh = random.random() < 0.5
        fv = random.random() < 0.5
        return _transform_pattern(base, rot, fh, fv)
    # Tenter de découvrir un nouveau pattern
    new_pat = _discover_random_feasible_pattern(max_tries=30)
    if new_pat is not None:
        _DYNAMIC_TEMPLATES.append(new_pat)
        return new_pat
    # Fallback template standard
    s = random.choice(_TEMPLATE_PATTERNS)
    base = _parse_template(s)
    rot = random.randint(0, 3)
    fh = random.random() < 0.5
    fv = random.random() < 0.5
    return _transform_pattern(base, rot, fh, fv)


def _each_row_col_has_black(blacks) -> bool:
    for r in range(GRID):
        if not any(blacks[r]):
            return False
    for c in range(GRID):
        if not any(blacks[r][c] for r in range(GRID)):
            return False
    return True


def generate_black_pattern(num_black_range=(10, 12), max_attempts=500) -> Optional[List[List[bool]]]:
    """Place des cases noires aléatoires respectant les contraintes:
    - 10 à 12 cases noires
    - cases blanches 4-connectées
    - au moins une case noire par ligne et par colonne (améliore feasibilité)
    """
    lo, hi = num_black_range
    for _ in range(max_attempts):
        n = random.randint(lo, hi)
        blacks = [[False] * GRID for _ in range(GRID)]
        cells = [(r, c) for r in range(GRID) for c in range(GRID)]
        random.shuffle(cells)
        placed = 0
        for r, c in cells:
            if placed >= n:
                break
            blacks[r][c] = True
            if not _white_connected(blacks):
                blacks[r][c] = False
                continue
            placed += 1

        if placed != n:
            continue
        if not _each_row_col_has_black(blacks):
            continue
        return blacks
    return None


# =============================================================================
# Segments
# =============================================================================

def compute_segments(blacks):
    segments: List[List[Tuple[int, int]]] = []
    cell_to_segs: dict = {}

    def flush(run):
        if len(run) >= 2:
            sid = len(segments)
            segments.append(run)
            for cell in run:
                cell_to_segs.setdefault(cell, []).append(sid)

    for r in range(GRID):
        run = []
        for c in range(GRID):
            if blacks[r][c]:
                flush(run)
                run = []
            else:
                run.append((r, c))
        flush(run)

    for c in range(GRID):
        run = []
        for r in range(GRID):
            if blacks[r][c]:
                flush(run)
                run = []
            else:
                run.append((r, c))
        flush(run)

    return segments, cell_to_segs


# =============================================================================
# Solveur par propagation
# =============================================================================

def _initial_domains(blacks, segments, cell_to_segs, hints):
    """Calcule les domaines initiaux pour chaque case blanche.

    Un domaine est un set de chiffres 1..6 possibles. Il est restreint par
    l'intersection des "valeurs possibles à cette position" pour chaque segment
    contenant la cellule, plus les indices fixes.
    """
    # Pour chaque segment, on part de tous les tuples valides pour sa longueur.
    seg_tuples = []
    for seg in segments:
        n = len(seg)
        tuples = _VALID_TUPLES.get(n, [])
        # Filtrer par hints éventuels
        filtered = []
        for t in tuples:
            ok = True
            for i, (r, c) in enumerate(seg):
                h = hints[r][c]
                if h not in (0, None) and t[i] != h:
                    ok = False
                    break
            if ok:
                filtered.append(t)
        seg_tuples.append(filtered)

    # Domaine par cellule = intersection des valeurs possibles par segment
    domains = {}
    for r in range(GRID):
        for c in range(GRID):
            if blacks[r][c]:
                continue
            h = hints[r][c]
            if h not in (0, None):
                domains[(r, c)] = {h}
                continue
            segs_here = cell_to_segs.get((r, c), [])
            if not segs_here:
                domains[(r, c)] = set(DIGITS)
                continue
            d_set = set(DIGITS)
            for sid in segs_here:
                idx = segments[sid].index((r, c))
                possible = {t[idx] for t in seg_tuples[sid]}
                d_set &= possible
            domains[(r, c)] = d_set
    return domains, seg_tuples


def _propagate(domains, segments, cell_to_segs, seg_tuples):
    """Arc consistency: réduit les domaines/tuples jusqu'à stabilité."""
    changed = True
    while changed:
        changed = False
        # Filtrer les tuples inconsistants avec les domaines actuels
        for sid, seg in enumerate(segments):
            before = len(seg_tuples[sid])
            seg_tuples[sid] = [
                t for t in seg_tuples[sid]
                if all(t[i] in domains[seg[i]] for i in range(len(seg)))
            ]
            if not seg_tuples[sid]:
                return False
            if len(seg_tuples[sid]) < before:
                changed = True

        # Recalculer les domaines depuis les tuples restants
        for cell, d_set in list(domains.items()):
            segs_here = cell_to_segs.get(cell, [])
            if not segs_here:
                continue
            new_d = set(DIGITS)
            for sid in segs_here:
                idx = segments[sid].index(cell)
                new_d &= {t[idx] for t in seg_tuples[sid]}
            if new_d != d_set:
                if not new_d:
                    return False
                domains[cell] = new_d
                changed = True
    return True


def _solve(blacks, segments, cell_to_segs, hints, limit=2, randomize=False, max_nodes=20000):
    """Solveur par propagation + backtracking MRV avec budget de nœuds."""
    domains, seg_tuples = _initial_domains(blacks, segments, cell_to_segs, hints)
    if not _propagate(domains, segments, cell_to_segs, seg_tuples):
        return []

    white_cells = [cell for cell in domains if len(domains[cell]) > 1]
    solutions = []
    node_count = [0]
    aborted = [False]

    def snapshot():
        out = [[0 if not blacks[r][c] else None for c in range(GRID)] for r in range(GRID)]
        for (r, c), s in domains.items():
            out[r][c] = next(iter(s))
        return out

    def bt():
        if aborted[0] or len(solutions) >= limit:
            return
        node_count[0] += 1
        if node_count[0] > max_nodes:
            aborted[0] = True
            return
        target = None
        best = 7
        for cell in white_cells:
            size = len(domains[cell])
            if 1 < size < best:
                best = size
                target = cell
                if size == 2:
                    break
        if target is None:
            solutions.append(snapshot())
            return

        vals = list(domains[target])
        if randomize:
            random.shuffle(vals)

        for v in vals:
            saved_domains = {k: set(s) for k, s in domains.items()}
            saved_tuples = [list(ts) for ts in seg_tuples]
            domains[target] = {v}
            if _propagate(domains, segments, cell_to_segs, seg_tuples):
                bt()
            for k, s in saved_domains.items():
                domains[k] = s
            for i, ts in enumerate(saved_tuples):
                seg_tuples[i] = ts
            if aborted[0] or len(solutions) >= limit:
                return

    bt()
    if aborted[0]:
        return None  # Budget épuisé : indéterminé
    return solutions


def count_solutions(hints, blacks, segments, cell_to_segs, limit=2, max_nodes=20000):
    """Retourne le nombre de solutions ou -1 si budget épuisé."""
    sols = _solve(blacks, segments, cell_to_segs, hints, limit=limit, randomize=False, max_nodes=max_nodes)
    if sols is None:
        return -1
    return len(sols)


def solve_one(blacks, segments, cell_to_segs, max_nodes=10000):
    """Trouve une solution aléatoire valide."""
    empty = [[0 if not blacks[r][c] else None for c in range(GRID)] for r in range(GRID)]
    sols = _solve(blacks, segments, cell_to_segs, empty, limit=1, randomize=True, max_nodes=max_nodes)
    if sols is None or not sols:
        return None
    return sols[0]


# =============================================================================
# Construction des indices
# =============================================================================

def _max_hints_per_segment(segment_len: int) -> int:
    return segment_len // 2


def _build_minimal_hints(solution, blacks, segments, cell_to_segs):
    """Construit un ensemble d'indices minimal via propagation.

    Stratégie: utiliser la propagation pour voir ce qui est "forcé" par
    les contraintes. Tant que des cellules restent libres, ajouter l'indice
    de la cellule au domaine le plus grand et re-propager.
    """
    hints = [[0 if not blacks[r][c] else None for c in range(GRID)] for r in range(GRID)]
    per_seg = [0] * len(segments)

    for _iter in range(GRID * GRID):
        # Propager les domaines avec les indices actuels
        domains, seg_tuples = _initial_domains(blacks, segments, cell_to_segs, hints)
        if not _propagate(domains, segments, cell_to_segs, seg_tuples):
            return None, None  # infeasible, shouldn't happen

        # Trouver les cellules non-forcées
        ambiguous = [(cell, len(d)) for cell, d in domains.items() if len(d) > 1]
        if not ambiguous:
            # Toutes les cellules sont forcées par propagation → unique
            placed = sum(1 for r in range(GRID) for c in range(GRID)
                         if not blacks[r][c] and hints[r][c] not in (0, None))
            return hints, placed

        # Ajouter l'indice sur la cellule avec le plus gros domaine (priorité)
        # en respectant la contrainte max/segment
        ambiguous.sort(key=lambda x: -x[1])
        added = False
        for (r, c), _size in ambiguous:
            segs_here = cell_to_segs.get((r, c), [])
            if any(per_seg[sid] + 1 > _max_hints_per_segment(len(segments[sid])) for sid in segs_here):
                continue
            hints[r][c] = solution[r][c]
            for sid in segs_here:
                per_seg[sid] += 1
            added = True
            break
        if not added:
            return None, None  # Plus de place sous la contrainte max/segment

    return None, None


def _pad_hints_to_target(hints, per_seg_counts, solution, blacks, segments,
                          cell_to_segs, target_count):
    """Ajoute des indices aléatoires jusqu'à atteindre target_count (respectant contraintes)."""
    current = sum(1 for r in range(GRID) for c in range(GRID)
                  if not blacks[r][c] and hints[r][c] != 0)
    empty = [(r, c) for r in range(GRID) for c in range(GRID)
             if not blacks[r][c] and hints[r][c] == 0]
    random.shuffle(empty)
    for r, c in empty:
        if current >= target_count:
            break
        segs_here = cell_to_segs.get((r, c), [])
        if any(per_seg_counts[sid] + 1 > _max_hints_per_segment(len(segments[sid])) for sid in segs_here):
            continue
        hints[r][c] = solution[r][c]
        for sid in segs_here:
            per_seg_counts[sid] += 1
        current += 1
    return hints, current


# =============================================================================
# Génération complète
# =============================================================================

def generate_puzzle(difficulty: str = "moyen",
                    enforce_unique_history: bool = True,
                    max_attempts: int = 40):
    hint_lo, hint_hi = DIFFICULTY_HINTS[difficulty]

    for _ in range(max_attempts):
        # Pattern connu faisable + transformation aléatoire (+ fallback random)
        blacks = _pick_pattern()
        segments, cell_to_segs = compute_segments(blacks)
        if not segments:
            continue
        if any(len(_VALID_TUPLES.get(len(s), [])) == 0 for s in segments):
            continue

        solution = solve_one(blacks, segments, cell_to_segs, max_nodes=200000)
        if solution is None:
            continue

        # Construire un set minimal d'indices
        minimal, min_count = _build_minimal_hints(solution, blacks, segments, cell_to_segs)
        if minimal is None:
            continue
        # Rejeter si le minimum dépasse la borne haute du niveau
        if min_count > hint_hi:
            continue

        # Compter les indices par segment pour pouvoir compléter
        per_seg = [0] * len(segments)
        for sid, seg in enumerate(segments):
            per_seg[sid] = sum(1 for (r, c) in seg if minimal[r][c] not in (0, None))

        target = random.randint(max(hint_lo, min_count), hint_hi)
        hints, actual = _pad_hints_to_target(minimal, per_seg, solution,
                                              blacks, segments, cell_to_segs, target)
        # On tolère actual légèrement ≠ target si la contrainte max/segment bloque
        if actual < hint_lo:
            continue

        if enforce_unique_history and not hist_unique(solution, blacks):
            continue

        n_hints_actual = sum(1 for r in range(GRID) for c in range(GRID)
                             if not blacks[r][c] and hints[r][c] != 0)
        n_blacks = sum(1 for r in range(GRID) for c in range(GRID) if blacks[r][c])

        puzzle = {
            'solution': solution,
            'blacks': blacks,
            'hints': hints,
            'segments': segments,
            'cell_to_segs': cell_to_segs,
            'difficulty': difficulty,
            'num_hints': n_hints_actual,
            'num_blacks': n_blacks,
        }

        if enforce_unique_history:
            add_to_history(solution, blacks, metadata={
                'difficulty': difficulty,
                'num_hints': n_hints_actual,
                'num_blacks': n_blacks,
            })

        return puzzle

    return None


def verify_puzzle(puzzle) -> bool:
    sol = puzzle['solution']
    blacks = puzzle['blacks']
    segments = puzzle['segments']
    cell_to_segs = puzzle['cell_to_segs']
    hints = puzzle['hints']

    for seg in segments:
        s = sum(sol[r][c] for (r, c) in seg)
        if s != TARGET_SUM:
            print(f"❌ Segment {seg}: somme {s} ≠ 10")
            return False
    for sid, seg in enumerate(segments):
        nh = sum(1 for (r, c) in seg if hints[r][c] not in (0, None))
        if nh > _max_hints_per_segment(len(seg)):
            print(f"❌ Segment {sid} len={len(seg)}: {nh} indices (max {_max_hints_per_segment(len(seg))})")
            return False
    if not _white_connected(blacks):
        print("❌ Cases blanches non connectées")
        return False
    n = count_solutions(hints, blacks, segments, cell_to_segs, limit=2)
    if n != 1:
        print(f"❌ {n} solutions")
        return False
    print(f"✅ Check X valide (noires={puzzle['num_blacks']}, indices={puzzle['num_hints']})")
    return True


def print_puzzle(puzzle):
    sol = puzzle['solution']
    blacks = puzzle['blacks']
    hints = puzzle['hints']
    print("\n--- Solution ---")
    for r in range(GRID):
        print(" ".join("■" if blacks[r][c] else str(sol[r][c]) for c in range(GRID)))
    print("\n--- Indices ---")
    for r in range(GRID):
        print(" ".join("■" if blacks[r][c] else (str(hints[r][c]) if hints[r][c] != 0 else ".")
                       for c in range(GRID)))


if __name__ == "__main__":
    import time
    print("Génération Check X moyenne...")
    t0 = time.time()
    p = generate_puzzle("moyen", enforce_unique_history=False)
    print(f"time: {time.time()-t0:.2f}s")
    if p:
        print_puzzle(p)
        verify_puzzle(p)
    else:
        print("❌ Échec")
