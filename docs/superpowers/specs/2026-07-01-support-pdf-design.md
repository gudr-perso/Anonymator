# Support PDF — Design

> **Statut** : validé en brainstorming, prêt pour plan d'implémentation.
> **Prérequis** : [conformité AGPL](2026-07-01-conformite-agpl-design.md) (PyMuPDF est
> AGPL-3.0). À traiter en parallèle, indépendant.

---

## 1. Objectif & périmètre

Ajouter le support des fichiers `.pdf` à Anonymator, avec **deux modes de sortie** :

1. **Rédaction juridique fidèle** — la mise en page d'origine est conservée, les entités
   détectées sont **réellement détruites** dans le flux du PDF (pas un simple masquage
   visuel), avec purge des métadonnées. Sortie = PDF ressemblant à l'original mais dont
   les données personnelles sont irrécupérables.
2. **Extraction texte anonymisée** — le texte est extrait, anonymisé via le pipeline
   texte existant, et exporté en `.txt` « à plat ». La mise en page est perdue, le
   contenu est propre.

**Périmètre v1 :**
- **PDF natifs uniquement** (texte sélectionnable). Les PDF scannés (image sans couche
  texte) sont **refusés** avec un message clair — OCR remis à une itération ultérieure.
- **Revue visuelle obligatoire** avant toute rédaction (irréversibilité).

**Hors périmètre v1 :** OCR / PDF scannés, RTL, ligatures/césure exotiques, sélection
de zones manuelle libre.

### Principe directeur

Le moteur de détection ne change pas. `detect()` et `apply_masking()` travaillent sur du
**texte plat + offsets de caractères**. Tout le travail PDF est une **traduction** entre
ce monde « texte plat » et le monde « géométrie de la page ». Le PDF n'ajoute aucune
logique de détection.

---

## 2. Outillage & licence

- **PyMuPDF** (fitz) : seule brique couvrant les 3 besoins — extraction texte avec
  coordonnées, **destruction réelle** du texte (`apply_redactions`), rendu de page en
  image pour l'aperçu. Un seul wheel, embarque MuPDF, compatible PyInstaller.
- **Licence AGPL-3.0** → repo public + `LICENSE` AGPL (cf. spec conformité). Coût 0 €.
- PyMuPDF est **isolé** dans le sous-package `anonymator/files/pdf/` : aucune autre partie
  du code ne l'importe directement, ce qui permet un remplacement futur si besoin.

---

## 3. Architecture

Nouveau sous-package `anonymator/files/pdf/` :

| Module | Rôle unique | Dépend de |
|---|---|---|
| `extract.py` | Ouvre, **classe natif/scanné**, extrait mots+boîtes, construit par page : texte plat + **carte offset→rectangles** | PyMuPDF (lecture) |
| `redact.py` | Reçoit entités retenues + rects → `add_redact_annot` + `apply_redactions` + purge métadonnées → sauvegarde | PyMuPDF (écriture) |
| `render.py` | Rend chaque page en image (pixmap→QImage) pour l'aperçu | PyMuPDF (rendu) |
| `pdf_io.py` | Orchestration. Expose `scan_pdf()`, `anonymize_pdf_redact()`, `anonymize_pdf_text()`. Miroir de `scan_csv`/`apply_csv` | les 3 ci-dessus |

Côté état de revue (core, non-Qt) :

- **`PdfReviewSession`** (`anonymator/core/pdf_review_session.py`) — miroir de
  `FileReviewSession`, indexé par `(page, rect)` au lieu de `(ligne, colonne)`. Mêmes
  niveaux de contrôle (type activé / valeur activée / exclusion individuelle). Produit
  les rects retenus par page + `report()`.

Côté UI :

- **`PdfScanWorker`** (`anonymator/ui/pdf_scan_worker.py`) — copie de `FileScanWorker`
  (scan threadé, signaux `scan_finished`/`error`).
- Extension de l'écran fichier (ou écran dédié) avec un **canevas d'image de page +
  overlays de rectangles**, réutilisant le panneau latéral d'entités existant.

### 3.1 Le pont détection→coordonnées (cœur du système)

1. `page.get_text("words")` → liste de `(x0,y0,x1,y1, texte, bloc, ligne, n°mot)`.
2. Reconstruction du **texte plat** de la page dans l'ordre de lecture, en maintenant
   un index `[(char_début, char_fin, rect), …]` par mot.
3. `detect(texte_page)` → entités avec offsets `[s, e)`.
4. Pour chaque entité : tous les mots dont la plage de caractères **recoupe** `[s, e)`
   → leurs rectangles → zones à caviarder. Entité multi-lignes → plusieurs rectangles.

**Contrat de sécurité** (testable) : après `apply_redactions()`, `page.get_text()` sur la
zone ne doit **plus** contenir la valeur d'origine.

---

## 4. Flux de données

### Mode rédaction (option 1)

```
PDF ─▶ extract.open ─▶ classify (natif ?) ─▶ scanné → ScannedPdfNotSupported
        │
        ▼ (par page) mots+rects → texte_page + carte offset→rects
        ▼ detect(texte_page) → entités confirmées
        ▼ REVUE : render pages en images + surlignage rects candidats
        │         utilisateur coche/décoche, CONFIRME
        ▼ (entités retenues) redact : offsets→rects → apply_redactions + purge méta
        ▼ PDF caviardé (destruction réelle) + AuditReport
```

La destruction n'a lieu **qu'après confirmation**. Avant, tout se joue sur l'aperçu rendu.

### Mode extraction texte (option 2)

```
PDF ─▶ extract : texte plat (toutes pages)
     ─▶ detect() ─▶ apply_masking()  (pipeline texte inchangé)
     ─▶ txt_io.write_text() → .txt anonymisé
```

Pas de géométrie, pas de revue visuelle (réutilise la revue « liste d'entités »).

### Réutilisé tel quel

`pipeline.detect`, `anonymize.apply_masking`, `AuditReport`, `output_naming.anonymized_path`,
`referential`, `txt_io.write_text`, le panneau latéral d'entités et le pattern worker/busy
de `FileScreen`. **L'original n'est jamais modifié** (comme les autres formats).

---

## 5. Gestion d'erreurs

| Cas | Détection | Comportement |
|---|---|---|
| PDF scanné (pas de couche texte) | `classify()` : quasi aucun mot extractible | `ScannedPdfNotSupported` → « PDF scanné : OCR non supporté pour l'instant » |
| PDF chiffré / protégé | PyMuPDF `needs_pass` | « PDF protégé par mot de passe : non supporté » |
| PDF corrompu / illisible | Exception à l'ouverture | « Fichier PDF illisible ou endommagé » |
| PDF mixte (pages scannées) | Ratio pages sans texte (heuristique) | Avertissement + traite les pages natives seules |
| Entité non mappable (offset sans rect) | Aucun mot ne recoupe l'offset | Log + fragment ignoré (ne bloque pas le reste) |

Aucun de ces cas ne provoque de plantage : tous remontent un message clair dans l'UI.

**Seuil de classification natif/scanné** : à calibrer à l'implémentation (ex. < N
caractères extractibles par page en moyenne → scanné). Valeur par défaut proposée et
ajustable, documentée dans le code.

---

## 6. Stratégie de tests (TDD)

Fixtures générées **par code** (PyMuPDF/reportlab), PII à positions connues, déterministes,
aucun binaire externe dans le repo.

| Test | Assertion | Priorité |
|---|---|---|
| **Destruction réelle** | Après rédaction, `get_text()` ne contient plus la valeur | ⭐ pivot |
| Extraction coords | Boîtes non vides + texte plat contient les PII | haute |
| Pont offset→rects | Entité `[s,e)` → bons rectangles (incl. multi-lignes) | haute |
| Purge métadonnées | Titre/auteur/mots-clés vidés | haute |
| Classification scanné | PDF image-only → `ScannedPdfNotSupported` | haute |
| Chiffré / corrompu | Message clair, pas de plantage | moyenne |
| Mode texte | Sortie `.txt` masquée correctement | moyenne |
| `PdfReviewSession` | Cases type/valeur → rects retenus corrects (non-Qt) | haute |

---

## 7. Impacts & packaging

- `requirements.txt` : ajouter `pymupdf`.
- `anonymator.spec` (PyInstaller) : vérifier l'embarquement de PyMuPDF (hidden imports /
  binaries MuPDF) — à valider au build.
- `README.md` : passer `.pdf` de ❌ à ✅ dans le tableau des formats + note « natifs
  uniquement, scannés non supportés ».
- `QFileDialog` : ajouter `*.pdf` au filtre une fois la feature prête.
- Taille de l'exe : PyMuPDF ajoute quelques Mo — acceptable.

---

## 8. Points ouverts

- Écran dédié PDF vs extension de `FileScreen` (à trancher au plan selon la complexité du
  canevas d'image + overlays).
- Seuil exact de classification natif/scanné (calibrage empirique).
- Choix de widget pour le canevas (`QGraphicsView` recommandé pour les overlays vectoriels
  vs `QLabel` + peinture manuelle).

---

## 9. Découpage pressenti (pour le plan)

1. `extract.py` + tests (ouverture, classification, mots+boîtes, texte plat).
2. Pont offset→rects + tests (le cœur logique).
3. `redact.py` + **test de destruction réelle** + purge métadonnées.
4. `render.py` + tests de rendu.
5. `pdf_io.py` orchestration + mode texte (réutilise pipeline).
6. `PdfReviewSession` (core, non-Qt) + tests.
7. `PdfScanWorker` + intégration UI (canevas + overlays + panneau réutilisé).
8. Packaging (requirements, spec PyInstaller, README, filtre QFileDialog).
