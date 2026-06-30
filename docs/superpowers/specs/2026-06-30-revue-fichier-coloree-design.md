# Revue fichier colorée — Doc de conception

> Écran de revue interactif pour le **mode Fichier** (CSV / FEC), avec colonnes éclatées,
> surlignage par typologie, contrôle à quatre niveaux et pagination.
> Brainstorming du 2026-06-30. Complète la spec d'origine
> [2026-06-29-anonymator-design.md](2026-06-29-anonymator-design.md) §6.

---

## 1. Contexte & problème

L'écran Fichier actuel ([`file_screen.py`](../../../anonymator/ui/file_screen.py)) est une version
minimale : aperçu brut du CSV puis « Anonymiser et enregistrer » qui masque et écrit **directement**,
sans revue. La revue colorée avec cases à cocher (maquette `revue-couleurs.html`) n'a été branchée
que sur le mode **Texte**. De plus, l'aperçu affiche tout le contenu **dans une seule colonne**
(bug de séparateur, voir §7).

Cette spec apporte au mode Fichier l'équivalent de la revue texte, **à la demande**, avec un contrôle
adapté aux fichiers comptables volumineux (FEC de plusieurs milliers de lignes).

**Hors périmètre de cette spec :**
- `.xlsx` : conserve le comportement direct actuel (anonymiser + enregistrer sans revue).
- Ajout manuel d'une entité manquée par sélection dans le tableau (évolution future).
- **Qualité de détection** (recall des IBAN/NIR plausibles, BIC/CP désactivés, logins, mots de
  passe) : sujet transverse traité dans un **spec dédié séparé**.

---

## 2. Périmètre des formats

| Format | « Analyser et revoir » | « Anonymiser et enregistrer » (direct) |
| --- | --- | --- |
| `.csv` | **Revue colorée tabulaire** (cœur de cette spec) | inchangé |
| `.txt` | Revue **texte** réutilisée (surlignage en flux, comme le mode Texte) | inchangé |
| `.xlsx` | Désactivé (bouton masqué/grisé) | inchangé |

Pour `.txt`, « Analyser et revoir » réutilise la logique de revue **texte** existante
(`ReviewSession` + surlignage en flux), **pas** la grille tabulaire : un fichier texte libre n'a pas
de colonnes. La grille colorée et le contrôle à 4 niveaux ne concernent donc que le `.csv`.

---

## 3. Flux utilisateur

L'écran Fichier garde **deux boutons d'action** :

1. **« Anonymiser et enregistrer »** — voie rapide, comportement actuel : détecte tout, masque ce que
   les règles par défaut retiennent, écrit le fichier. Pas de revue.
2. **« Analyser et revoir »** — nouveau : lance la détection sur les colonnes masquables (dédupliquée)
   **dans un thread de fond avec barre de progression**, puis bascule l'écran en **mode revue**.

Pendant le scan, les boutons sont désactivés et un libellé indique l'avancement. À l'ouverture d'un
nouveau fichier, on revient à l'aperçu simple (pas de revue tant qu'on n'a pas cliqué « Analyser et
revoir »).

En mode revue :
- tableau éclaté par colonnes, paginé 20 lignes, cellules PII surlignées par typologie ;
- panneau latéral **droit** : typologies (compteurs) dépliables en valeurs distinctes, toutes cochables ;
- cases inclure/exclure dans les **en-têtes de colonnes** ;
- bas : pagination + actions **« Appliquer et enregistrer »** et **« Exporter le rapport »**.

Disposition validée (maquette `layout-v1.html`) : tableau à gauche, panneau à droite, pagination +
actions en bas.

---

## 4. Architecture des modules

Principe inchangé du projet : **la logique vit hors de Qt**, testable isolément ; les widgets Qt sont
des vues minces.

- **`anonymator/core/file_review_session.py`** (nouveau, non-Qt) — `FileReviewSession`.
  Détient le `CsvDocument`, la map `cellule (r,c) → entités détectées`, l'index des **valeurs
  distinctes par type**, et l'état d'activation (types, valeurs, colonnes, cellules exclues).
  API :
  - `types() -> list[str]` (types présents, avec ordre stable)
  - `values_for(type) -> list[(valeur, count)]`
  - `count_retained(type) -> int`
  - `set_type_enabled(type, bool)` / `set_value_enabled(type, valeur, bool)`
  - `set_column_enabled(col, bool)` / `set_cell_excluded(r, c, bool)`
  - `entities_for_cell(r, c) -> list[Entity]` (retenues uniquement → pilote le surlignage)
  - `masked_document() -> CsvDocument`
  - `report() -> AuditReport` (retenues uniquement)

- **Refactor `anonymator/files/anonymize_file.py`** — extraire de `anonymize_csv` :
  - `scan_csv(doc, ner, ref, cols) -> dict[(r,c), list[Entity]]` : la détection dédupliquée.
  - `apply_csv(doc, retained_by_cell, ref) -> (CsvDocument, AuditReport)` : masque + rapport.
  - `anonymize_csv` devient `scan_csv` + `apply_csv` avec tout activé → le bouton direct et les
    tests existants restent valides (non-régression).

- **`anonymator/ui/file_scan_worker.py`** (nouveau) — `QThread` qui exécute `scan_csv` et émet
  progression + résultat (modèle [`download_worker.py`](../../../anonymator/ui/download_worker.py)).

- **`anonymator/ui/file_screen.py`** (réécrit) — coquille mince : deux sous-vues (aperçu / revue),
  tableau paginé, panneau latéral. Toute la logique d'état déléguée à `FileReviewSession`.

- **Correctif `anonymator/files/csv_io.py`** — `sniff_delimiter` échantillonne sur des **lignes
  entières** (retirer la dernière ligne partielle de l'échantillon) pour ne plus retomber sur `;`
  par défaut. Voir §7.

---

## 5. Modèle de contrôle & préséance du masquage

Les quatre niveaux se combinent par un **ET logique**. Une cellule `(r, c)` portant une valeur
détectée `v` de type `t` est **masquée si et seulement si** :

1. la **colonne** `c` est incluse, **ET**
2. le **type** `t` est activé, **ET**
3. la **valeur distincte** `v` est activée, **ET**
4. la cellule `(r, c)` n'est **pas exclue individuellement**.

Comportements :
- **Défauts** : colonnes = `default_maskable_columns` (règle D existante) ; tous types et valeurs
  activés. La revue part de « tout masqué » ; l'utilisateur **retire** ce qu'il veut garder en clair.
- **Décocher un type** grise/barre toutes ses valeurs et son surlignage. **Décocher une valeur**
  ne touche que ses occurrences. **Clic sur une cellule surlignée** bascule l'exclusion de *cette*
  occurrence seule.
- **Exclure une colonne** la sort de l'analyse (cellules non surlignées) ; les détections restent en
  mémoire → **ré-inclure une colonne est instantané**, sans relancer GLiNER.
- Le **compteur** d'une typologie compte les occurrences **actuellement retenues** et se met à jour
  à chaque (dé)cochage.

---

## 6. Pagination & rendu

- **Pagination côté données** : 20 lignes de données par page, en-tête figé. Navigation
  **Première / Préc. / Suiv. / Dernière**, indicateur **« page X / N »**, champ **« Aller à »**
  (validé par Entrée ; valeur hors bornes ramenée dans `[1, N]`).
- Le **panneau latéral** et les **cases de colonnes** sont **globaux** (agissent sur tout le fichier,
  pas la page courante) et restent visibles quelle que soit la page.
- **Rendu d'une cellule** : si elle porte ≥1 entité retenue → surlignage à la **couleur du type**
  ([`colors.py`](../../../anonymator/ui/colors.py)) ; cellule exclue individuellement = barrée/atténuée ;
  colonnes exclues grisées.
- **Performance d'affichage** : on ne peuple que les ~20 `QTableWidgetItem` de la page courante à
  chaque changement de page (jamais les milliers de lignes d'un coup).

---

## 7. Correctif du séparateur CSV (bug « tout dans une colonne »)

`sniff_delimiter` échantillonne `text[:4096]`, ce qui coupe la **dernière ligne en plein milieu**.
Le nombre de `|` n'est alors plus constant sur toutes les lignes de l'échantillon → `|` est rejeté
→ repli sur `;` par défaut (absent d'un FEC) → tout le contenu atterrit dans une seule colonne.

**Correctif** : construire l'échantillon à partir de **lignes complètes** uniquement (retirer la
dernière ligne si l'échantillon est tronqué, ou lire N lignes entières). Test de non-régression :
un FEC séparé par `|` plus long que 4096 octets doit donner `delimiter == "|"` et des lignes
correctement éclatées.

---

## 8. Rapport d'audit

« Exporter le rapport » reflète **les seules entités retenues** au moment de l'export (après les
décochages), pas la détection brute. Format CSV/JSON comme l'existant. Avertissement « contient des
valeurs sensibles » conservé.

---

## 9. Cas limites

- FEC > 4096 octets → séparateur `|` correctement détecté (test du correctif §7).
- Fichier sans en-tête → colonnes nommées `col0, col1…` ; la sélection opère sur les index.
- Cellule à plusieurs entités ; valeurs identiques dans des colonnes différentes ; lignes plus
  courtes que l'en-tête (déjà géré par `c < len(row)`).
- Détection longue → thread de fond, UI non figée, boutons désactivés pendant le scan ; ré-inclure
  une colonne ne relance pas la détection.
- `.xlsx` → inchangé (voie directe), « Analyser et revoir » désactivé pour ce format.

---

## 10. Tests (TDD)

Cœur non-Qt :
- `test_file_review_session.py` : préséance des 4 niveaux ; compteurs de retenus ; `masked_document` ;
  `report` (type décoché, valeur décochée, cellule exclue, colonne exclue).
- `test_anonymize_file.py` : `scan_csv`/`apply_csv` équivalents à l'ancien `anonymize_csv` quand tout
  est activé (non-régression).
- `test_csv_io.py` : correctif sniff sur échantillon tronqué.

Vue Qt (pytest-qt, smoke) :
- `test_file_screen.py` : ouvrir → analyser (FakeNer) → la session se peuple ; pagination
  (première/dernière/aller à) ; appliquer → fichier écrit ; bouton direct toujours fonctionnel ;
  bouton revue désactivé pour `.xlsx`.

---

## 11. Décisions verrouillées (récapitulatif)

1. Revue colorée **optionnelle** via un second bouton « Analyser et revoir » ; voie directe conservée.
2. Contrôle à **4 niveaux** combinés en ET : type, valeur distincte, colonne, cellule.
3. Formats : **CSV** (revue tabulaire) + **txt** (revue texte réutilisée) ; **xlsx** inchangé.
4. Pagination **20 lignes/page** ; navigation première/préc./suiv./dernière + « aller à ».
5. Disposition : tableau à gauche, panneau typologies/valeurs à droite, pagination + actions en bas.
6. Architecture : `FileReviewSession` non-Qt + refactor `scan_csv`/`apply_csv` + worker thread +
   vue mince + correctif sniff.
