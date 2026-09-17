"""Porteurs de texte d'un classeur que la grille des cellules ne montre pas.

`scan_workbook` ne lit que `cell.value` : c'est le périmètre visible à l'écran,
et c'est celui que la revue présente. Mais un classeur range du texte à quatre
autres endroits, tous invisibles à la relecture et tous recopiés intacts dans le
fichier produit :

- **les commentaires de cellule**, avec le nom de leur auteur. C'est précisément
  là qu'on note ce qu'on ne veut pas mettre dans la cellule (coordonnées
  personnelles, appréciation sur un salarié) ; ils ne s'affichent qu'au survol,
  donc ils ne sont jamais relus ;
- **les en-têtes et pieds de page**, qui portent régulièrement le nom du
  destinataire d'un tableau de bord. Le module Word les traite depuis toujours,
  le classeur était le seul à les ignorer ;
- **les noms définis**, dont le texte peut être une chaîne littérale ;
- **les littéraux d'une formule** : `="Dupont"&A2` garde le nom dans la barre de
  formule. La cellule de formule n'est jamais réécrite, à raison — l'écraser
  détruirait le calcul — mais ses littéraux, eux, se masquent sans y toucher.

Chaque porteur est exposé comme un « run » (objet à attribut `.text` mutable),
ce qui les fait passer par le même pipeline de détection, de masquage et de
rapport que le reste du projet.
"""
import re

from anonymator.files.ooxml.text_unit import TextUnit

# Littéral de formule Excel : entre guillemets doubles, un guillemet interne
# étant doublé (« ="Jean ""Jeannot"" Dupont" »).
_FORMULA_LITERAL_RE = re.compile(r'"(?:[^"]|"")*"')

# Les six jeux d'en-tête et de pied qu'une feuille peut porter, et leurs trois
# zones. Une donnée nominative peut ne figurer que sur la première page.
_HEADER_SLOTS = (
    ("oddHeader", "En-tête"), ("oddFooter", "Pied"),
    ("evenHeader", "En-tête (pages paires)"), ("evenFooter", "Pied (pages paires)"),
    ("firstHeader", "En-tête (1re page)"), ("firstFooter", "Pied (1re page)"),
)
_HEADER_ZONES = ("left", "center", "right")


class _AttrRun:
    """Run sur un attribut d'objet (`comment.text`, `part.text`, `attr_text`)."""

    def __init__(self, obj, attribute: str):
        self._obj, self._attr = obj, attribute

    @property
    def text(self) -> str:
        return getattr(self._obj, self._attr, None) or ""

    @text.setter
    def text(self, value: str) -> None:
        setattr(self._obj, self._attr, value)


class _CommentRun:
    """Run sur le texte d'un commentaire de cellule.

    openpyxl lie le commentaire à sa cellule : muter l'objet en place suffit,
    il est resérialisé tel quel à l'enregistrement."""

    def __init__(self, cell, attribute: str = "text"):
        self._cell, self._attr = cell, attribute

    @property
    def text(self) -> str:
        c = self._cell.comment
        return (getattr(c, self._attr, None) or "") if c is not None else ""

    @text.setter
    def text(self, value: str) -> None:
        if self._cell.comment is not None:
            setattr(self._cell.comment, self._attr, value)


class _FormulaLiteralRun:
    """Run sur le n-ième littéral chaîne d'une formule.

    Ne touche ni aux références, ni aux opérateurs, ni aux noms de fonction :
    seul le contenu entre guillemets est réécrit, donc la formule reste
    calculable. C'est ce qui permet de masquer `="Dupont"&A2` sans détruire le
    calcul que l'exclusion des cellules de formule protège par ailleurs."""

    def __init__(self, cell, index: int):
        self._cell, self._index = cell, index

    def _spans(self):
        return list(_FORMULA_LITERAL_RE.finditer(str(self._cell.value or "")))

    @property
    def text(self) -> str:
        spans = self._spans()
        if self._index >= len(spans):
            return ""
        return spans[self._index].group(0)[1:-1].replace('""', '"')

    @text.setter
    def text(self, value: str) -> None:
        spans = self._spans()
        if self._index >= len(spans):
            return
        raw = str(self._cell.value or "")
        m = spans[self._index]
        escaped = '"' + value.replace('"', '""') + '"'
        self._cell.value = raw[:m.start()] + escaped + raw[m.end():]


def _is_formula(cell) -> bool:
    return cell.data_type == "f" or (isinstance(cell.value, str)
                                     and cell.value.startswith("="))


def comment_units(ws) -> list[TextUnit]:
    """Texte et auteur de chaque commentaire de la feuille."""
    units: list[TextUnit] = []
    for row in ws.iter_rows():
        for cell in row:
            if cell.comment is None:
                continue
            where = f"{ws.title}!{cell.coordinate}"
            units.append(TextUnit([_CommentRun(cell, "text")],
                                  f"Commentaire {where}"))
            if (getattr(cell.comment, "author", None) or "").strip():
                units.append(TextUnit([_CommentRun(cell, "author")],
                                      f"Commentaire {where} / Auteur"))
    return units


def header_footer_units(ws) -> list[TextUnit]:
    """Les trois zones de chacun des six jeux d'en-tête et de pied."""
    units: list[TextUnit] = []
    for attr, label in _HEADER_SLOTS:
        block = getattr(ws, attr, None)
        if block is None:
            continue
        for zone in _HEADER_ZONES:
            part = getattr(block, zone, None)
            if part is None or not (getattr(part, "text", None) or "").strip():
                continue
            units.append(TextUnit([_AttrRun(part, "text")],
                                  f"{ws.title} / {label}"))
    return units


def formula_units(ws) -> list[TextUnit]:
    """Un TextUnit par littéral chaîne des formules de la feuille."""
    units: list[TextUnit] = []
    for row in ws.iter_rows():
        for cell in row:
            if not _is_formula(cell):
                continue
            n = len(_FORMULA_LITERAL_RE.findall(str(cell.value or "")))
            for i in range(n):
                units.append(TextUnit([_FormulaLiteralRun(cell, i)],
                                      f"{ws.title}!{cell.coordinate} (formule)"))
    return units


def _defined_name_values(holder):
    names = getattr(holder, "defined_names", None)
    if names is None:
        return []
    values = names.values() if hasattr(names, "values") else names
    return [d for d in values if (getattr(d, "attr_text", None) or "").strip()]


def defined_name_units(workbook) -> list[TextUnit]:
    """Noms définis du classeur et des feuilles."""
    units = [TextUnit([_AttrRun(d, "attr_text")], f"Nom défini « {d.name} »")
             for d in _defined_name_values(workbook)]
    for ws in workbook.worksheets:
        units += [TextUnit([_AttrRun(d, "attr_text")],
                           f"{ws.title} / Nom défini « {d.name} »")
                  for d in _defined_name_values(ws)]
    return units


def hidden_text_units(workbook) -> list[TextUnit]:
    """Tous les porteurs de texte hors grille, pour une feuille comme pour le
    classeur. Rassemblés en une seule liste : ils suivent tous le même chemin,
    détection puis masquage des seules entités confirmées."""
    units: list[TextUnit] = []
    for ws in workbook.worksheets:
        units += comment_units(ws)
        units += header_footer_units(ws)
        units += formula_units(ws)
    units += defined_name_units(workbook)
    return units


def drop_pivot_caches(workbook) -> int:
    """Retire les tableaux croisés dynamiques et leur cache. Renvoie le nombre
    de caches retirés.

    Un cache de tableau croisé est une **copie littérale des lignes source**,
    conservée dans `xl/pivotCache/`. Masquer les cellules de la feuille source
    n'y touche pas : le classeur sort avec les données d'origine, lisibles en
    dézippant le fichier ou par « afficher les détails » sur une cellule du
    tableau croisé. On passe par le modèle d'openpyxl plutôt qu'en découpant le
    zip après coup : supprimer les parties à la main laisserait des relations et
    des types de contenu orphelins, et Excel proposerait de réparer le fichier.
    """
    removed = 0
    for ws in workbook.worksheets:
        pivots = getattr(ws, "_pivots", None)
        if pivots:
            removed += len(pivots)
            ws._pivots = []
    return removed
