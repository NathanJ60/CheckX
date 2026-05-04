#!/usr/bin/env python3
"""Vérification d'unicité dédiée pour Check 10.

Module séparé (comme check_unique_go8.py pour 8-GO), il fournit une API
dédiée pour verifier qu'un puzzle Check 10 a **exactement une solution**
(pas zéro, pas plusieurs), indépendamment du générateur.

Approche en deux phases:
1. Trouver UNE solution via le solveur CSP interne (propagation + MRV).
2. Tenter de trouver une 2e solution; si impossible, la grille est unique.
"""

import time
from typing import List, Optional

from check10_model import (
    GRID, TARGET_SUM, DIGITS,
    compute_segments, count_solutions, _solve,
)


def check_uniqueness(blacks, hints, original_solution=None,
                     timeout: float = 30.0, verbose: bool = False):
    """Vérifie si le puzzle Check 10 a une solution unique.

    Args:
        blacks: grille booléenne (True = case noire)
        hints: grille d'indices (0 = inconnu, 1..6 = valeur, None = case noire)
        original_solution: solution attendue (optionnel) — si fournie, on
            verifie aussi que l'unique solution trouvee correspond.
        timeout: budget temps total (secondes)
        verbose: affichage détaillé

    Returns:
        True  -> solution unique (et == original_solution si fourni)
        False -> 0 ou ≥2 solutions, ou differe de l'originale
        None  -> indéterminé (budget epuise)
    """
    t0 = time.time()

    segments, cell_to_segs = compute_segments(blacks)
    if not segments:
        if verbose:
            print("  [UNICITE] Aucun segment à verifier")
        return True

    num_hints = sum(1 for r in range(GRID) for c in range(GRID)
                    if hints[r][c] not in (0, None))
    num_whites = sum(1 for r in range(GRID) for c in range(GRID)
                     if not blacks[r][c])
    num_blacks = GRID * GRID - num_whites

    if verbose:
        print(f"  [UNICITE] Grille {GRID}×{GRID}: {num_blacks} noires, "
              f"{num_whites} blanches, {num_hints} indices visibles, "
              f"{len(segments)} segments")

    # Phase 1 : trouver UNE solution
    budget = int(timeout * 100000)  # ~100K nodes/s estimé
    solutions = _solve(blacks, segments, cell_to_segs, hints,
                       limit=1, randomize=False, max_nodes=budget)

    if solutions is None:
        if verbose:
            print("  [UNICITE] ? Budget epuise (phase 1)")
        return None

    if not solutions:
        if verbose:
            print("  [UNICITE] ECHEC: Aucune solution")
        return False

    sol1 = solutions[0]

    if verbose:
        print(f"  [UNICITE] OK: Solution trouvee en {time.time()-t0:.3f}s")

    # Vérifier correspondance avec la solution attendue
    if original_solution is not None:
        matches = all(
            sol1[r][c] == original_solution[r][c]
            for r in range(GRID) for c in range(GRID)
            if not blacks[r][c]
        )
        if not matches:
            if verbose:
                print("  [UNICITE] ECHEC: Solution differe de l'originale")
            return False

    # Phase 2 : chercher une 2e solution via count_solutions(limit=2)
    remaining = timeout - (time.time() - t0)
    if remaining <= 0:
        if verbose:
            print("  [UNICITE] ? Timeout avant phase 2")
        return None

    budget2 = int(remaining * 100000)
    n = count_solutions(hints, blacks, segments, cell_to_segs,
                        limit=2, max_nodes=budget2)

    if n == -1:
        if verbose:
            print("  [UNICITE] ? Budget epuise (phase 2)")
        return None

    if n >= 2:
        if verbose:
            print("  [UNICITE] ECHEC: 2e solution trouvee -> NON UNIQUE")
        return False

    if n == 0:
        if verbose:
            print("  [UNICITE] ECHEC: Paradoxe : 0 solution phase 2 ?")
        return False

    if verbose:
        print(f"  [UNICITE] OK: UNIQUE ({time.time()-t0:.3f}s)")
    return True


def verify_constraints(puzzle, verbose: bool = False):
    """Vérifie que toutes les contraintes Check 10 sont respectees.

    Contraintes:
    1. Entre 10 et 12 cases noires
    2. Cases blanches 4-connectees
    3. Aucune paire de cases noires 4-adjacentes (touchement diagonal seul)
    4. Tout segment ≥2 cases somme à 10 (via la solution)
    5. Max floor(len/2) indices par segment
    6. Solution unique
    """
    from check10_model import _white_connected, _max_hints_per_segment, _no_adjacent_blacks

    blacks = puzzle['blacks']
    hints = puzzle['hints']
    sol = puzzle['solution']
    segments = puzzle['segments']

    errors = []

    # [1] Nombre de cases noires
    nb = sum(1 for r in range(GRID) for c in range(GRID) if blacks[r][c])
    if not (10 <= nb <= 12):
        errors.append(f"cases noires = {nb} (hors 10-12)")

    # [2] Connectivité des blanches
    if not _white_connected(blacks):
        errors.append("cases blanches non 4-connectees")

    # [3] Pas de cases noires 4-adjacentes
    if not _no_adjacent_blacks(blacks):
        errors.append("cases noires 4-adjacentes (interdit, seulement diagonale)")

    # [3] Somme 10 par segment
    for sid, seg in enumerate(segments):
        s = sum(sol[r][c] for (r, c) in seg)
        if s != TARGET_SUM:
            errors.append(f"segment {sid} (len {len(seg)}) somme={s} != 10")

    # [4] Max indices par segment
    for sid, seg in enumerate(segments):
        nh = sum(1 for (r, c) in seg if hints[r][c] not in (0, None))
        max_allowed = _max_hints_per_segment(len(seg))
        if nh > max_allowed:
            errors.append(f"segment {sid} (len {len(seg)}) {nh} indices > max {max_allowed}")

    # [5] Unicité
    unique = check_uniqueness(blacks, hints, original_solution=sol,
                              timeout=10.0, verbose=verbose)
    if unique is not True:
        errors.append(f"unicité = {unique}")

    if verbose:
        if errors:
            print("  ECHEC: Erreurs:")
            for e in errors:
                print(f"    - {e}")
        else:
            print("  OK: Toutes les contraintes respectees")

    return len(errors) == 0, errors


if __name__ == "__main__":
    from check10_model import generate_puzzle

    print("=" * 60)
    print("Test d'unicité Check 10")
    print("=" * 60)

    for diff in ["difficile", "moyen", "facile"]:
        print(f"\n[{diff.upper()}]")
        p = generate_puzzle(diff, enforce_unique_history=False)
        if not p:
            print(f"  ECHEC: Generation echouee")
            continue

        ok, errors = verify_constraints(p, verbose=True)
        status = "OK:" if ok else "ECHEC:"
        print(f"  {status} {diff}: "
              f"{p['num_blacks']} noires, {p['num_hints']} indices")
