# Amélioration & uniformisation de la détection PDF

Date : 2026-07-01
Statut : design validé

## Problème

Sur un même document PDF, des données identiques sont détectées à un
endroit et pas à un autre — sur la même page comme d'une page à l'autre.
Exemple : l'adresse « 16 RUE JEROME BONAPARTE » est surlignée dans le bloc
« Lieu de consommation » mais pas dans un bloc isolé en haut de page,
alors qu'elle figure bien dans la liste des entités détectées.

### Causes identifiées

1. **Une entité = une position → un seul surlignage.** Le pipeline détecte
   une entité à un offset unique ; `mapping.rects_for_entity` ne caviarde
   que les mots recoupant ce span. Les occurrences identiques ailleurs ne
   sont pas propagées. *(cause directe du symptôme visible)*
2. **GLiNER est sensible au contexte.** `PERSON` / `ADDRESS` / `ORG` ne
   reposent que sur GLiNER (aucune règle). Le score d'un même span passe
   au-dessus du seuil dans un contexte riche et en dessous dans un bloc
   isolé → « même donnée, détectée ici, pas là ».
3. **La reconstruction de l'ordre de lecture casse le contexte.**
   `extract_page` trie par `(bloc, ligne, mot)` et détecte sur une seule
   chaîne par page ; le texte de marge pivoté et les colonnes s'entrelacent
   et coupent les phrases, dégradant le rappel de GLiNER.

## Portée

Trois axes retenus : **A** (propagation), **C** (adresse déterministe),
**D-léger** (ordre de lecture). Exclus volontairement (YAGNI) :

- **B** — baisse du seuil GLiNER.
- **D-lourd** — détection GLiNER par bloc (coût vitesse trop élevé pour un
  gain marginal une fois A en place).
- Propagation des valeurs **non confirmées**.

## Décisions de cadrage

- **Propagation (A) : tout le document.** Une valeur confirmée quelque part
  est caviardée à toutes ses occurrences, sur toutes les pages.
- **Ordre de lecture (D) : version légère**, sans surcoût de vitesse et sans
  régression de caviardage.

## Architecture & flux

Point d'insertion unique : `scan_pdf` dans `anonymator/files/pdf/pdf_io.py`.
L'UI, la revue (`PdfReviewSession`) et le caviardage restent **inchangés** :
ils profitent des occurrences supplémentaires via le regroupement existant
`(type, valeur)` avec compteur `×N`.

Nouveau flux dans `scan_pdf` :

1. **Extraction** des pages avec ordre de lecture amélioré (D).
2. **Détection par page** via `detect()` existant, incluant le regex
   adresse (C).
3. **Propagation tout-document** (A) : collecte des valeurs sensibles
   confirmées de toutes les pages, recherche de toutes leurs occurrences sur
   chaque page, fusion.

## C — Adresse déterministe

Un motif ajouté à `_PATTERNS` dans `anonymator/deterministic.py`, type
`ADDRESS`, compilé avec `re.IGNORECASE` :

- forme : `<numéro>[ bis/ter/quater] <type-de-voie> <reste de la ligne>` ;
- types de voie : rue, avenue/av, bd/boulevard, impasse, allée/allee,
  chemin, place, route, quai, cours, passage, square, villa,
  résidence/residence (liste extensible) ;
- s'arrête au saut de ligne (`[^\n]*`) → capture « 16 RUE JEROME BONAPARTE »
  seule ; le code postal reste géré par `POSTAL_CODE`, la ville par GLiNER ;
- `confirmed=True` (pas de validateur) → coché par défaut.

`ADDRESS` est déjà un type actif du référentiel (produit par GLiNER). Comme
`source="deterministic"` prime dans `merge_entities`, aucun doublon n'est
créé avec une détection GLiNER au même endroit.

## D — Ordre de lecture (léger)

Dans `extract_page` (`anonymator/files/pdf/extract.py`) :

- regrouper les mots par bloc ; calculer la bbox de chaque bloc ;
- classer un bloc comme **vertical** si ses mots sont majoritairement plus
  hauts que larges (texte de marge pivoté) ;
- ordonner : blocs horizontaux d'abord, triés par bande verticale (y) puis
  par x ; blocs verticaux **relégués en fin de flux** ;
- à l'intérieur d'un bloc, conserver l'ordre `(ligne, mot)`.

Contrat préservé : `PageText(text, words)` avec offsets `char_start`/
`char_end` cohérents avec `text`, car texte plat et `WordBox` sont construits
dans la même boucle quel que soit l'ordre des blocs. Aucun effet sur le
caviardage (les rectangles restent liés aux mots).

## A — Propagation (nouveau module `anonymator/files/pdf/propagate.py`)

Signature :

```python
def propagate_across_pages(
    pages: list[PageText],
    per_page_entities: list[list[Entity]],
) -> list[list[Entity]]:
    ...
```

- **Sources** : entités `confirmed=True` de toutes les pages →
  dictionnaire `valeur normalisée → (type, valeur canonique)` via
  `textnorm.normalize`. La valeur canonique est la première rencontrée, pour
  que le panneau regroupe toutes les occurrences sous une seule ligne `×N`.
- **Garde-fous anti-sur-détection** : ignorer une valeur si
  - elle est purement numérique (évite que « 16 » se propage partout), ou
  - c'est un **seul token de moins de 3 caractères**.
  Les valeurs multi-tokens sont toujours propagées.
- **Correspondance par tokens de mots** (jamais par sous-chaîne) : glissement
  sur les `WordBox` de chaque page, repérage des suites consécutives dont les
  tokens normalisés égalent ceux de la cible. Un match produit
  `Entity(type, valeur_canonique, char_start_du_1er, char_end_du_dernier,
  source="propagated", 1.0, confirmed=True)`. Le matching token-entier
  élimine tout faux positif intra-mot.
- **Fusion** : `merge_entities(originales + propagées)` par page. Les
  chevauchements sont dédupliqués ; `deterministic` reste prioritaire.

Nouvelle valeur `source="propagated"` : aucun code existant ne s'y casse
(`merge._rank` ne teste que `deterministic` ; report, session et le filtre
`confirmed` sont agnostiques à la source).

## Tests

- **`tests/test_pdf_propagate.py`** (nouveau) : détection unique propagée à
  toutes les occurrences (y compris multi-pages) ; garde-fous (numérique pur,
  token court) ne sur-détectent pas ; regroupement `×N` correct après fusion.
- **`tests/test_pdf_extract.py`** : ordre de lecture — phrases contiguës dans
  un bloc, marge verticale reléguée ; fixture 2 colonnes + marge.
- **Test déterministe existant** : cas `ADDRESS` (variantes de casse et de
  types de voie ; non-capture au-delà du saut de ligne).
- **`tests/test_pdf_io.py`** : `scan_pdf` de bout en bout avec propagation
  active (occurrence non détectée initialement mais propagée).

## Risques

- **D** : sur une mise en page très atypique, l'ordre des blocs peut rester
  imparfait, mais jamais pire qu'aujourd'hui et sans effet sur le caviardage.
- **C** : le regex adresse peut capturer une ligne non pertinente commençant
  par « <nombre> <type-de-voie> » ; l'utilisateur décoche en revue.
- **A** : la propagation d'un prénom court reste bornée par le matching
  token-entier et le garde-fou de longueur minimale.
