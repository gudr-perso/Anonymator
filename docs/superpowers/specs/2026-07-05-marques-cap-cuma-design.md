# Confidentialisation des thèmes — deux marques verrouillées (CAP / CUMA)

Date : 2026-07-05
Statut : conception validée, prêt pour plan d'implémentation

## Objectif

Diffuser deux exécutables distincts, chacun figé nativement dans « le bon » thème,
non modifiable par l'utilisateur, et portant un nom de produit propre :

- **Cum'Anonyme** — thème `cuma` (vert)
- **CAP'nonyme** — thème `cap` (bleu)

Un troisième mode **dev**, non verrouillé, conserve le sélecteur de thème et les
deux thèmes pour le développement interne (non diffusé).

## Niveau de confidentialité retenu

**Verrou UI uniquement.** L'exe force son thème et masque le sélecteur ; les deux
thèmes restent techniquement présents dans le binaire. On ne cherche pas
l'étanchéité totale (exclusion du thème adverse du build). Conséquence assumée :
un utilisateur qui extrait les chaînes du binaire pourrait retrouver l'autre
thème ; ce n'est pas dans le périmètre.

## Concept central : la « marque »

On introduit une notion de **marque** au-dessus du **thème** existant. Une marque
est un paquet cohérent regroupant tout ce qui distingue une version diffusée.

| Champ          | CUMA          | CAP          | Dev (non verrouillé) |
|----------------|---------------|--------------|----------------------|
| `key`          | `cuma`        | `cap`        | —                    |
| `theme`        | `cuma`        | `cap`        | libre (préférences)  |
| `product_name` | `Cum'Anonyme` | `CAP'nonyme` | `Anonymator`         |
| `exe_name`     | `cumanonyme`  | `capnonyme`  | `anonymator`         |
| `icon`         | `anonymator.ico` (par défaut ; icône dédiée possible plus tard) |
| `locked`       | `True`        | `True`       | `False`              |

Le thème n'est pas supprimé : il devient l'un des champs de la marque. La couche
`theme.py` (dict `THEMES`, `build_qss`, logos, `header_tag`) reste inchangée.

## Architecture

### Nouveau module `anonymator/brand.py`

Sur le modèle exact de `theme.py` (état global + accesseurs) :

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Brand:
    key: str
    theme: str
    product_name: str
    exe_name: str
    icon: str
    locked: bool

BRANDS = {
    "cuma": Brand("cuma", "cuma", "Cum'Anonyme", "cumanonyme", "anonymator.ico", True),
    "cap":  Brand("cap",  "cap",  "CAP'nonyme",  "capnonyme",  "anonymator.ico", True),
}

_DEV_BRAND = Brand("dev", None, "Anonymator", "anonymator", "anonymator.ico", False)

_active = _DEV_BRAND   # par défaut : dev, non verrouillé

def lock_brand(key: str) -> None:
    global _active
    _active = BRANDS[key]

def active_brand() -> Brand:
    return _active

def is_locked() -> bool:
    return _active.locked
```

- Aucune marque verrouillée par défaut → comportement dev (identique à aujourd'hui).
- `lock_brand("cap"|"cuma")` fige la marque *avant* la construction de la fenêtre.

### Mécanisme de verrou au démarrage

La différence entre les deux exe tient à **une seule chose** : quel module
d'entrée appelle `lock_brand(...)` avant `main()`.

```
cumanonyme.exe
  └─ anonymator/brands/cuma.py
        lock_brand("cuma")        ──▶ marque active = CUMA (locked=True)
        main()                    ──▶ MainWindow lit la marque :
                                        titre  = product_name
                                        thème  = brand.theme (ignore preferences.json)
                                        settings: sélecteur masqué (is_locked())
```

En **mode verrouillé**, `MainWindow` prend le thème depuis la marque, pas depuis
`preferences.json` : un exe CUMA reste en CUMA même si le fichier de préférences
contient `theme: "cap"`. En **mode dev**, aucun `lock_brand` n'est appelé → thème
depuis les préférences, sélecteur visible, deux thèmes disponibles (comportement
actuel intact).

### Modules d'entrée par marque

- `anonymator/brands/__init__.py` (vide)
- `anonymator/brands/cuma.py` :
  ```python
  from anonymator.brand import lock_brand
  from anonymator.__main__ import main
  if __name__ == "__main__":
      lock_brand("cuma")
      raise SystemExit(main())
  ```
- `anonymator/brands/cap.py` : idem avec `"cap"`.

### Injection du branding (nom produit)

Le libellé « Anonymator » est aujourd'hui en dur à trois endroits ; tous passent
par `active_brand().product_name` :

- `anonymator/ui/main_window.py` → `setWindowTitle(...)`
- `anonymator/ui/components/header.py` → nom du bandeau
- `anonymator/ui/about.py` → ligne « À propos »

`about.py` conserve l'URL du dépôt et le tag de version (conformité AGPL : le code
source reste le même dépôt public ; seul le nom d'affichage change).

### Verrou du thème et masquage du sélecteur

- `anonymator/ui/main_window.py` : au démarrage et dans `_apply_theme`, le thème
  effectif est `active_brand().theme` si `is_locked()`, sinon `prefs.theme`
  (comportement actuel). En mode verrouillé, un changement de thème ne peut pas
  survenir puisque le sélecteur est masqué.
- `anonymator/ui/settings_screen.py` : la sous-section « Thème de l'application »
  (label + `theme_box`) n'est construite/ajoutée que si `not is_locked()`.

## Build

### Spec paramétré (un seul `.spec`)

`anonymator.spec` est paramétré par une variable d'environnement **de build**
`ANONYMATOR_BUILD_BRAND` (lue au packaging, pas au runtime) valant `cap`, `cuma`
ou `dev` :

- `cap` / `cuma` → script analysé = `anonymator/brands/<brand>.py`,
  `EXE(name=<exe_name>)`, `COLLECT(name=<exe_name>)`, icône de la marque.
- `dev` (ou absent) → comportement actuel : `anonymator/__main__.py`, exe
  `anonymator`.

Cela évite de dupliquer le `.spec` (une seule source de vérité pour `datas` /
`hiddenimports`).

### Script `scripts/build.ps1`

Argument : `cap` | `cuma` | `dev` | `all`.

Pour chaque marque demandée :
1. `ANONYMATOR_BUILD_BRAND=<brand>` puis `pyinstaller anonymator.spec` avec
   l'interprète du venv (`.venv\Scripts\python.exe -m PyInstaller`, cf. mémoire
   build-env).
2. Zippe `dist/<exe_name>/` en `dist/<Nom>-v<version>.zip`, où `<version>` est lue
   depuis `anonymator/__init__.py` (`__version__`). Noms de zip :
   - `CumAnonyme-v<version>.zip`
   - `CAPnonyme-v<version>.zip`
   - (dev : pas de zip par défaut)

`all` produit `cap` + `cuma` (dev exclu de la diffusion).

### Résultat par version diffusée

Deux zips autonomes, ~95 % identiques (le poids vient des dépendances partagées :
PySide6, torch, transformers…). Duplication du volume assumée — c'est le prix de
deux exe autonomes. Hors périmètre pour l'instant : installeur commun, exe
one-file.

## Tests

- `tests/test_brand.py` :
  - défaut = dev, `is_locked()` faux, `product_name == "Anonymator"` ;
  - `lock_brand("cap")` → thème `cap`, `product_name == "CAP'nonyme"`, verrouillé ;
  - `lock_brand("cuma")` → thème `cuma`, `product_name == "Cum'Anonyme"`.
- `tests/test_main_window_theme.py` (ajustement) : en mode verrouillé, un
  `preferences.json` portant l'autre thème est ignoré ; le thème appliqué est
  celui de la marque.
- `tests/test_settings_screen.py` (ajustement) : sélecteur de thème présent en dev,
  absent en mode verrouillé.

## Hors périmètre

- Étanchéité totale (exclusion du thème adverse du binaire).
- Icônes dédiées par marque (le champ `icon` existe ; on branchera un `.ico`
  spécifique plus tard si besoin).
- Réduction du volume des zips (installeur commun, one-file).
```
