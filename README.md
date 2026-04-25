# Check 10

Générateur de puzzles Check 10 : grille 8×8 où chaque segment de ≥2 cases consécutives (entre cases noires ou bords) doit sommer à 10.

## Règles

- Grille 8×8 avec des **cases blanches** (à remplir) et **cases noires** (séparateurs).
- Placer les chiffres **1 à 6** dans les cases blanches.
- Tout **segment** (suite de cases blanches consécutives, horizontale ou verticale, entre deux bords ou cases noires) de **longueur ≥ 2** doit avoir une **somme égale à 10**.
- Les segments de longueur 1 (une case isolée) sont sans contrainte.

## Contraintes de génération

- **10 à 12 cases noires** par grille.
- **Cases blanches 4-connectées** (la grille ne doit pas être "coupée" en régions isolées).
- **Max `floor(len/2)` indices par segment** (évite par exemple 3 indices sur un segment de 4).

## Niveaux de difficulté

| Niveau     | Nombre d'indices |
|------------|------------------|
| Difficile  | 10–13            |
| Moyen      | 12–15            |
| Facile     | 14–17            |

## Architecture

```
check10_model.py            Générateur + solveur CSP par propagation + templates
check10_model_history.py    Historique persistant hash-based
check10_visualization.py    Rendu PNG (noir et blanc, style PDF officiel)
check10_gui.py              Interface PyQt5
consigne/                  Règles officielles (PDF)
design/                    Screenshots de référence
```

## Génération : stratégie hybride

1. **Templates** : 2 patterns de cases noires connus faisables (dérivés du PDF officiel), multipliés par les **8 symétries D4** (rotations + flips) → 16 patterns de base.
2. **Fallback aléatoire** : génération de nouveaux patterns aléatoires validés par propagation rapide, avec cache dynamique.
3. Pour chaque pattern, le **solveur CSP** :
   - Pré-calcule tous les tuples valides par longueur (2..8) sommant à 10
   - Propagation d'arc consistency (filtre tuples ↔ domaines)
   - Backtracking MRV avec budget de nœuds
4. **Unicité garantie** : chaque puzzle retourné est vérifié par `count_solutions` (exactement 1 solution).

## Utilisation

```bash
python -m venv venv
source venv/bin/activate
pip install PyQt5 Pillow
python check10_gui.py
```

Ou en ligne de commande :

```python
from check10_model import generate_puzzle, verify_puzzle
from check10_visualization import draw_check10

puzzle = generate_puzzle("moyen")
verify_puzzle(puzzle)
draw_check10(puzzle, "mon_puzzle")
```

## Garantie d'unicité

Chaque puzzle a une **solution unique** vérifiée par le solveur avant retour. La diversité est assurée par :
- L'historique persistant (`data/check10_history.json`) qui rejette les doublons entre appels
- La randomisation des chiffres via le solveur (chaque pattern admet des centaines de solutions différentes)
- Le fallback aléatoire pour découvrir de nouveaux patterns au-delà des templates
