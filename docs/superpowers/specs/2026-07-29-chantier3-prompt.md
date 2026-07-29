# Chantier 3 — Sélection par colonne + revue XLSX

## Contexte

Projet `C:\_pCloud\Extensions\anonymise` (application Qt/PySide6 d'anonymisation
RGPD de fichiers, français). Environnement : `.venv\Scripts\python.exe`.
Suite de tests : `.venv/Scripts/python.exe -m pytest -q` — elle doit rester
verte de bout en bout (~529 tests aujourd'hui).

Un chantier précédent a remplacé la détection cellule par cellule par une
**classification par colonne**. Il est terminé, testé, et ne doit pas être
refait — lis-le avant de commencer :

- `anonymator/files/columns.py` — `classify_columns()` produit un plan par
  colonne avec trois politiques : `TYPED` (type connu par l'en-tête ou par un
  contenu homogène → la cellule entière est l'entité, le NER n'est pas
  appelé), `TEXT` (règles + NER), `SKIP` (mesures numériques, nomenclatures).
- `anonymator/pipeline.py::detect_column()` — détection d'une cellule de
  colonne typée.
- `anonymator/files/anonymize_file.py::csv_column_plans()` — plan CSV avec
  `include` / `exclude` / `has_header` explicites.
- `anonymator/files/xlsx_io.py` — même classification, appliquée par feuille.

## Objectif

Deux besoins qui attaquent la même surface d'interface. **Les traiter
ensemble** : séparément, on écrit deux fois l'UI de colonnes et on découvre au
second passage que le premier découpage ne convenait pas.

### A. Clic sur l'en-tête de colonne (CSV et XLSX)

Trois états par colonne, pilotés depuis l'en-tête du tableau d'aperçu :

1. **Auto** — le plan calculé par `classify_columns` (défaut).
2. **Tout anonymiser** — toutes les cellules non vides de la colonne sont
   masquées, y compris celles où aucun détecteur n'a rien vu.
3. **Tout libérer** — la colonne sort du périmètre.

L'état courant et sa raison doivent être lisibles : `ColumnPlan` porte déjà un
champ `reason` renseigné (`en-tête « telephone »`, `nomenclature (peu de
valeurs distinctes)`, `valeurs numériques`…) — l'exposer, par exemple en
infobulle sur l'en-tête.

**Point dur.** L'état 2 n'existe aujourd'hui sur aucun chemin.
`FileReviewSession` ne sait que *retirer* : `_cell_retained()` filtre des
entités déjà détectées, et `set_column_enabled()` ne fait que désactiver.
Masquer une cellule sur décision de colonne demande un chemin neuf. Piste
recommandée : réutiliser `pipeline.detect_column()`, qui fabrique une entité
couvrant la cellule entière — c'est déjà ce que fait la politique `TYPED`.
Le forçage manuel devient alors « appliquer `TYPED` à cette colonne », avec un
type à choisir ou à déduire.

### B. Ouvrir la revue aux fichiers `.xlsx`

Aujourd'hui `btn_review` est désactivé pour `.xlsx`
(`anonymator/ui/file_screen.py:201`), `load_path` laisse `self.doc` à `None`,
aucun aperçu n'est affiché : le classeur part directement au masquage. Il n'y
a donc ni décochage d'entité, ni interrupteur d'en-tête, ni clic colonne.

Forme retenue : **grille, calquée sur le CSV** — une feuille à la fois via un
sélecteur, cellules affichées, surlignage par type, pagination, interrupteur
« première ligne = en-têtes » par feuille.

La forme « liste d'unités » (comme docx/pptx, via `_render_units_page`) a été
écartée : elle est presque gratuite mais perd la lecture tabulaire, donc
l'objet même du chantier. Ne pas y revenir sans raison nouvelle.

## Inventaire du code concerné

| Fichier | Rôle | Ce qu'il faut en faire |
|---|---|---|
| `anonymator/files/xlsx_io.py` (92 l.) | lit, classe, scanne, masque, sauve en une passe | **séparer scan et application**, sur le modèle de `anonymator/files/ooxml/scan.py` (`scan` / `apply_units`). Un `XlsxScanResult` doit porter classeur, feuilles, plans, `has_header` et `scanned`. |
| `anonymator/core/file_review_session.py` (129 l.) | revue CSV, clé `(ligne, colonne)` | source de la future session XLSX |
| `anonymator/core/ooxml_review_session.py` (99 l.) | revue docx/pptx, clé `index d'unité` | — |
| *(à créer)* `XlsxReviewSession` | clé `(feuille, ligne, colonne)` | ~130 l., dont 80 % recopiées |
| `anonymator/ui/file_scan_worker.py` (21 l.) | scan CSV hors thread UI | modèle du `XlsxScanWorker` (obligatoire : un gros classeur ne se scanne pas sur le thread UI) |
| `anonymator/ui/file_screen.py` (613 l.) | l'écran | le gros du travail |

## Décisions déjà prises — ne pas les rejouer

- **La classification par colonne reste le défaut.** Le clic colonne est un
  **override explicite** de l'utilisateur, pas un remplacement du plan auto.
- **`(type, valeur)` est la clé des arbitrages manuels**, jamais la position.
  C'est ce qui leur permet de survivre à un changement de plan (voir
  `_capture_choices` / `_restore_choices` dans `file_screen.py`). Un override
  de colonne, lui, est positionnel par nature : décider s'il survit à un
  changement d'hypothèse d'en-tête, et le tester.
- **`POSTAL_CODE`, `BIC` et `URL` sont inactifs** dans
  `anonymator/config/entities.json`. Une colonne typée dont le type est
  inactif ne produit rien : c'est voulu, ce n'est pas un bug.

## Pièges relevés

1. **`_render_units_page()` ne pagine pas** — il rend *toutes* les unités d'un
   coup. Acceptable pour un docx, gel de l'interface sur une feuille de
   100 000 lignes. Toute reprise de ce code pour XLSX doit paginer.
2. **`isinstance(self.session, OoxmlReviewSession)`** sert déjà de dispatch à
   deux endroits (`run()`, `_on_side_changed()`). À trois sessions il faut une
   méthode polymorphe, pas un troisième `elif`.
3. **La comptabilité types/valeurs est dupliquée mot pour mot** entre
   `FileReviewSession` (l. 24-33) et `OoxmlReviewSession` (l. 25-33). Ajouter
   une troisième copie serait la faute : factoriser une base commune d'abord.
4. **`csv.Sniffer().has_header` est instable** — sur `Nom;Montant` il voit un
   en-tête avec une ligne de données, plus aucun avec deux. D'où
   l'interrupteur manuel côté CSV. Côté XLSX, `xlsx_io.sheet_has_header()`
   s'appuie sur les types réels des cellules et n'a ce trou que sur une
   feuille intégralement textuelle.
5. **`_data_rows()` / `_page_count()` / `_render_page()` supposent
   `self.doc.rows`** (structure CSV). Les généraliser avant d'y brancher une
   feuille de calcul.
6. **Ne jamais réécrire une cellule de formule** (`_is_formula` dans
   `xlsx_io.py`), et ne pas la compter dans le profil d'une colonne.

## Contraintes de réalisation

- **TDD** : test rouge d'abord, c'est la convention du dépôt (~529 tests).
- Tests UI avec `pytest-qt` (`qtbot`), plateforme offscreen déjà configurée
  dans `tests/conftest.py`.
- Commentaires et libellés **en français**, ton du dépôt : expliquer le
  *pourquoi*, pas le *quoi*.
- Ne pas modifier les tests existants pour les faire passer — s'ils cassent,
  c'est une régression à traiter.
- Vérifier sur `exemples/clients_demo.csv` (120 lignes, colonnes mêlant
  identités, nomenclatures et mesures) et sur sa conversion `.xlsx`.

## Hors périmètre

- Refaire la classification par colonne.
- La revue des `.docx` / `.pptx` (déjà en place, ne pas y toucher).
- Le format `.txt` (chemin séparé).
