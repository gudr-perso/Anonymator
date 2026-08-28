# Anonymator — État du projet & comment continuer

> Point de reprise. Lis ce fichier en premier quand tu rouvres le projet (y compris depuis un autre PC).
> Dernière mise à jour : 2026-08-28.

---

## Où on en est

Application locale Windows d'**anonymisation** (non réversible) de texte et de fichiers comptables/bureautiques,
diffusée en **deux marques verrouillées** (Cum'Anonyme = CUMA vert, CAP'nonyme = CAP bleu).
Développement piloté par specs + plans, en TDD, exécution par sous-agents avec revue.

| Étape | État |
|---|---|
| **Plan 1 — moteur de détection & anonymisation texte** | ✅ **Fait, sur `main`** |
| **Plan 2 — E/S fichiers (txt/csv/xlsx) + rapport d'audit** | ✅ **Fait, sur `main`** |
| **Plan 3 — application UI PySide6** | ✅ **Fait, sur `main`** |
| **Plan 4 — packaging PyInstaller + README + 1er téléchargement modèle** | ✅ **Fait, sur `main`** |
| **Expérience GLiNER « zéro friction » (non bloquant + mode dégradé)** | ✅ **Fait, sur `main`** |
| **Conformité AGPL + versionnage taggé** (déclenché par PyMuPDF) | ✅ **Fait** — `LICENSE` AGPL-3.0, tags `v0.2.0` → `v0.5.1` posés |
| **Support PDF** (rédaction juridique réelle + extraction texte) | ✅ **Fait — `v0.2.0`** (PyMuPDF, revue visuelle, propagation, ordre de lecture) |
| **Règles métier utilisateur** (allow/force par motif, `[REGLE-INTERNE]`) | ✅ **Fait** — écran « Gestion des règles » dédié |
| **Éclatement des Paramètres** (Paramètres / Gestion des règles / À propos) | ✅ **Fait** |
| **Refonte des écrans + refonte thème CAP** | ✅ **Fait** |
| **Anonymisation Office (.docx / .pptx)** + purge métadonnées | ✅ **Fait — `v0.3.0`** |
| **Marques verrouillées CAP / CUMA** (thème figé, nom produit, sélecteur masqué) | ✅ **Fait — `v0.4.0`** (build paramétré par marque) |
| **Chantier « colonnes + revue XLSX »** (plan par colonne, forçage manuel, revue feuille par feuille) | ✅ **Fait — `v0.5.0`/`v0.5.1`**, fusionné sur `main` |
| **Landing page Cum'Anonyme** (`html/index.html`, autonome) | ✅ **Fait** — DL vers le partage pCloud, renvoi vers la doc utilisateur |
| **Documentation utilisateur publiée** (Notion, neutre par édition) | ✅ **Fait — 2026-08-28** |
| Export du **rapport d'audit** depuis l'UI | ⬜ **Non exposé** — `report/audit.py` est prêt et alimenté par les sessions, il manque le bouton |
| Test d'intégration GLiNER (modèle réel) | ⬜ **Jamais lancé** (voir `docs/installation-gliner.md`) |
| Installeur Windows (setup.exe + raccourcis + code signing) | ⬜ **Pas commencé** — « Plan 5 » (brainstorming dédié à faire) |

**Tests : 615 verts + 1 d'intégration désélectionné** (`.venv/Scripts/python -m pytest -q` → `615 passed, 1 deselected`, ~18 s).
Le test d'intégration ne nécessite `torch` que si on lance `-m integration`.

**Version courante : `0.5.1`** (`anonymator/__init__.py` = source de vérité, dupliquée dans `pyproject.toml`).

## Ce qui est diffusable aujourd'hui

- `dist/CAPnonyme-v0.5.1.zip` et `dist/CumAnonyme-v0.5.1.zip` (~289 Mo chacun, **non versionnés**),
  construits le 2026-07-30 à partir de `v0.5.1`. Chaque archive contient l'exe, `_internal/`,
  `LICENSE` à la racine et le dossier `exemples/`.
- **Lien de téléchargement public** (partage pCloud, pointé par la landing page) :
  <https://e.pcloud.link/publink/show?code=kZGb777ZMvQqHnFYHu5GQNY9hwOaXuABmzA7>
- **Documentation utilisateur** (neutre par édition, publiée) :
  <https://capconsulting.notion.site/anonymator-documentation-utilisateur>
  — page Notion source dans la base *CAP Extensions - Documentation*.

> **Neutralité de marque dans la doc.** La doc utilisateur et le `README.md` sont communs aux deux
> éditions : ils ne nomment **jamais** Cum'Anonyme ni CAP'nonyme, parlent du « projet Anonymator »
> et désignent l'exécutable comme « le `.exe` à la racine du dossier dézippé, qui porte le nom de
> votre édition ». Garder cette règle à chaque mise à jour.
> Corollaire : les captures de `docs/img/` sont des **visuels CAP** (logo incrusté) — inutilisables
> telles quelles dans un document commun.

## Prochaine action

Le produit est livré (texte, csv/xlsx avec raisonnement par colonne, PDF, docx/pptx, règles métier,
deux marques, landing page, doc utilisateur). Pistes ouvertes, par ordre de valeur :

1. **Installeur Windows** (« Plan 5 ») : brainstorming dédié — `setup.exe` (Inno Setup ?), raccourcis menu Démarrer,
   éventuel **code signing** (supprimerait l'avertissement SmartScreen documenté dans la doc utilisateur).
   Un seul installeur par marque (réutilise `scripts/build.ps1` qui zippe déjà par marque).
2. **Validation manuelle des exes des deux marques** : dérouler le scénario GLiNER « zéro friction » (démarrage sans
   modèle → mode dégradé → téléchargement guidé) sur `dist/…/*.exe`, et vérifier le verrou de thème (sélecteur masqué).
3. **Exposer le rapport d'audit** : la brique moteur existe et est déjà alimentée (y compris la purge des
   métadonnées Office), aucun écran ne propose de l'exporter. Décider où (fin de traitement ? Paramètres ?)
   et prévenir que le rapport contient les **valeurs d'origine en clair**.
4. **Test d'intégration GLiNER** (modèle réel) : toujours jamais exécuté (`docs/installation-gliner.md`).
5. **Bug connu de la landing page** : le `<span class="mark">` du `<h1>` est en `white-space:nowrap` et
   **déborde horizontalement en dessous de ~400 px** de large. Corriger sans casser le surlignage orange.

Rappel modèle éco : Anonymator est **open source AGPL-3.0** (repo public) à cause de PyMuPDF ; monétisation par
**prestation** (install/formation/support), pas par vente de licence/clé (inopposable en AGPL).

Méthode utilisée jusqu'ici : skill `superpowers:subagent-driven-development` (un sous-agent par tâche, revue conformité + qualité, branche dédiée puis fusion).

---

## Carte du code (sur `main`)

```
anonymator/
  model.py            Entity (dataclass span)
  validators.py       Luhn, IBAN mod97, NIR, BIC (pays ISO), code postal FR
  deterministic.py    détecteurs regex+checksum -> Entities
  secrets_detect.py   heuristique d'entropie (mots de passe/secrets)
  textnorm.py         normalisation de texte pour la détection
  merge.py            résolution des chevauchements (déterministe > confiance > longueur)
  ner.py              NerDetector (protocole), FakeNer (tests), NullNer (mode dégradé), GlinerDetector (réel, torch paresseux)
  dedup.py            détecte une fois par valeur unique
  referential.py      référentiel JSON (anonymator/config/entities.json)
                      active_codes() = détection auto ; forceable_codes() = forçage manuel (inclut les inactifs + MASK)
  user_rules.py       règles métier utilisateur (keep/mask par motif, mode simple/regex)
  pipeline.py         detect(text, ner, ref) : déterministe ∥ NER -> merge
                      detect_column(value, etype, ref, force=False) : cellule d'une colonne typée
  anonymize.py        apply_masking(text, entities, ref) -> texte [CATÉGORIE]
  output_naming.py    <nom>_ano_AAAAMMJJHHMMSS.<ext>
  brand.py            marque = surcouche thème + nom produit (CAP / CUMA / dev)
  brands/             cap.py, cuma.py : points d'entrée verrouillés (build paramétré)
  files/              encoding, csv_io, columns (plan TYPED/TEXT/SKIP par colonne),
                      txt_io, xlsx_io (scan_workbook / apply_workbook), anonymize_file (orchestrateur + dispatcher)
    pdf/              pdf_io, extract, mapping, redact (caviardage réel PyMuPDF), render, propagate
    ooxml/            docx_io, pptx_io, scan, run_remap, text_unit, xml_parts, metadata (purge)
  report/audit.py     AuditReport (agrégation + export CSV/JSON) — brique moteur, PAS exposée dans l'UI
  core/               model_status (dispo/taille cache GLiNER), model_download (DL HuggingFace + progression),
                      chunking, risk,
                      review_session_base -> tabular_review_session -> file_review_session (CSV) / xlsx_review_session,
                      review_session (texte), ooxml_review_session, pdf_review_session
  ui/                 PySide6 : main_window (démarrage non bloquant, thème piloté par marque),
                      home_screen (bandeau d'onglets, repli logo par marque), settings_screen (allégé),
                      rules_screen (gestion des règles), about_screen / about (mentions AGPL + contact),
                      text_screen, file_screen (grille, pagination, sélecteur de feuille, menu d'en-tête de colonne),
                      pdf_screen + pdf_canvas (aperçu image + overlays + zoom),
                      workers QThread (text_analyze, file_scan/anonymize, xlsx_scan, ooxml_scan, pdf_scan, download),
                      model_loader, preferences, colors, entity_meta, icons, theme, components/
tests/                un fichier de test par module (TDD) — 99 fichiers, 615 tests verts
exemples/             jeu de démonstration à données fictives (clients_demo.csv/.xlsx, compte_rendu_reunion_demo.pdf),
                      copié à la racine du dossier distribué par build.ps1 ; couvert par test_demo_dataset.py
html/index.html       landing page Cum'Anonyme (autonome, CSS inline, logos base64)
scripts/              build.ps1 (build + zip par marque), make_ico.py
docs/                 ETAT-PROJET.md (ce fichier), DOCUMENTATION.md (v2.0, les 3 parties), RELEASE.md,
                      installation-gliner.md, changements-2026-07-29-colonnes-xlsx.md,
  img/                captures d'écran 0.5.1 (visuels CAP) + copies de travail
  superpowers/        specs/ (conception + journal) et plans/ (1-4, GLiNER, PDF, règles, docx/pptx, marques, colonnes…)
```

## Décisions verrouillées (rappel)

- **v1 = anonymisation seule** ; pseudonymisation / relais Anthropic / vault = v2.
- Détection floue = **GLiNER** (pas Ollama) ; substitution **déterministe** (« le code dispose »).
- **Deux marques diffusées, thème verrouillé** : **Cum'Anonyme** (CUMA vert) et **CAP'nonyme** (CAP bleu).
  L'exe force son thème et **masque le sélecteur** (verrou UI seulement ; les 2 thèmes restent dans le binaire).
  Un mode **dev** non verrouillé garde le sélecteur (non diffusé). Titres Space Grotesk, texte Inter.
- Couleurs **fonctionnelles** par type d'entité = jeu **fixe** (indépendant du thème).
- **BIC**, **code postal** et **URL** implémentés mais **inactifs par défaut** (bruyants sur FEC ; activables).
- **ORG masqué par défaut** (banques incluses).
- **Règles métier utilisateur** : moteur **symétrique** `keep` (allow-list) / `mask` (force-list → `[REGLE-INTERNE]`),
  par **motif** (simple avec jokers, ou regex expert), éditables **sans toucher au code** et **partageables**.
- **Tableaux : on raisonne par colonne**, pas par cellule. Plan `TYPED` / `TEXT` / `SKIP` calculé par `columns.py`,
  avec garde-fous plein-cadre, garde « identifiant » et cardinalité à deux critères. L'hypothèse
  « première ligne = en-têtes » est **tranchée par l'utilisateur** (`csv.Sniffer` est instable), par feuille en XLSX.
- **Un forçage manuel de colonne prime sur le référentiel** : `detect_column(..., force=True)` court-circuite
  `is_active`, le menu propose **tous** les types (inactifs signalés) plus le pseudo-type neutre `MASK` → `[MASQUÉ]`,
  jamais produit par la détection auto. Les règles « conserver » restent prioritaires.
- **GLiNER non bloquant** : l'app démarre toujours ; sans le modèle → **mode dégradé** (règles déterministes seules +
  bannière). Téléchargement guidé (barre % réelle) depuis l'accueil ou Paramètres ; reprise sans redémarrage.
- **GLiNER tronque > ~384 tokens** : découper le texte **avant** le NER (piège rencontré sur PDF).
- **Exe windowed** : `sys.stdout`/`sys.stderr` sont `None` → garde-fou dans `anonymator/__main__.py`.
- **PDF** : PDF **natifs uniquement** (scannés refusés, OCR plus tard), **2 modes** (rédaction juridique = destruction
  réelle via PyMuPDF + extraction texte), **revue visuelle obligatoire** avant destruction ; propagation tout-document
  des valeurs confirmées + ordre de lecture. PyMuPDF isolé dans `anonymator/files/pdf/`.
- **Office .docx/.pptx** : remap mutualisé, **revue par liste d'entités** (pas de rendu visuel), couverture cœur +
  périphérique, **purge systématique des métadonnées** d'identité tracée dans l'audit.
- **Sessions de revue** : une hiérarchie unique (`ReviewSessionBase` → `TabularReviewSession` → CSV/XLSX,
  plus `OoxmlReviewSession` et `PdfReviewSession`), `_index()` **rejouable** (aucun compte différentiel),
  et `apply_and_save(out_path)` commun — l'écran n'a pas à connaître le format.
- **Licence** : **AGPL-3.0** (imposé par PyMuPDF) → repo public + `LICENSE` AGPL ; **pas** de licence commerciale
  Artifex. Versionnage : **tag `vX.Y.Z` par release**, pas par commit ; `__version__` unique lu par l'UI.
  GLiNER `urchade/gliner_multi-v2.1` = Apache-2.0 (usage commercial OK).

---

## Environnement & pièges (IMPORTANT sur un nouveau PC)

- **Python** : sur la machine d'origine, `python`/`python3` sont des stubs Windows Store → toujours `.venv/Scripts/python`. Sur un autre PC, vérifier l'interpréteur ; recréer le venv si besoin :
  `python -m venv .venv` puis `.venv/Scripts/python -m pip install -r requirements.txt`.
- **Version de Python** : venv reconstruit en **3.14.6** le 2026-07-29 (il était en 3.13, désinstallé depuis). Toute la pile a des wheels 3.14 (torch 2.13, PySide6 6.11.1, PyMuPDF 1.28, gliner 0.2.28) ; les tests passent et les deux exes se lancent. Aucune version de Python n'est épinglée : vérifier la disponibilité des wheels `cp3XX` avant de sauter de version.
- **Le `.venv/` n'est pas dans git** (voir `.gitignore`). À recréer sur chaque machine.
- **pCloud + grosses dépendances** : `torch` (via gliner) et `PySide6` pèsent des centaines de Mo. Avant de les installer, **exclure `.venv/` de la synchro pCloud** (ou créer le venv hors du dossier pCloud). Détails : `docs/installation-gliner.md`. Après un build complet le dossier contient ~3,9 Go non versionnés (`.venv` 1,6 Go, `dist` 2,0 Go, `build` 344 Mo).
- **`.git` synchronisé par pCloud** : branche/historique/fichiers peuvent changer en cours de session → vérifier l'état (`git status`, `git log`) avant de committer. **Le `.git` peut aussi disparaître purement et simplement** (constaté le 2026-07-29) : le dossier reste complet mais n'est plus un dépôt. Remède : `git clone` du remote ailleurs, puis recopier son `.git/` dans le dossier de travail — `git status` révèle alors ce qui n'avait pas été poussé.
- **Fins de ligne** : `core.autocrlf=true` ici, mais certains blobs du dépôt ont été poussés en CRLF depuis une autre machine → ces fichiers apparaissent modifiés en permanence alors que `git diff` est vide. Ne pas les committer (commit de blancs) ; nettoyer un jour d'un coup avec `git add --renormalize .`.
- **Lancer les tests** : `.venv/Scripts/python -m pytest -q` (→ `615 passed, 1 deselected`). Plateforme offscreen gérée automatiquement via `tests/conftest.py`.
- **Lancer l'appli** : `.venv/Scripts/python -m anonymator` (mode dev, sélecteur de thème actif).
- **Builder les exes** : `scripts/build.ps1 cap|cuma|dev|all` (spec paramétré par `ANONYMATOR_BUILD_BRAND`, zippe par marque, copie le `LICENSE` **et le dossier `exemples/`** à la racine du dossier distribué). Compter ~4 min par marque. **Ne pas rediriger la sortie avec `2>&1`** : PyInstaller écrit ses `INFO` sur stderr, PowerShell les transforme en erreurs et le `$ErrorActionPreference = 'Stop'` du script avorte le build dès la première ligne.

## Git / remote

- Remote : `https://github.com/gudr-perso/Anonymator.git`, branche `main`.
- **Pousser** : sur la machine d'origine, le compte git par défaut (`gudr-cuma`) n'a pas les droits → l'URL du remote embarque `gudr-perso@` pour forcer le bon jeton. **Sur un autre PC**, configurer l'authentification GitHub du compte **gudr-perso** (sinon `403`). Si besoin :
  `git remote set-url origin https://gudr-perso@github.com/gudr-perso/Anonymator.git`
- Convention : une branche `feat/...` par plan, fusion dans `main` après revue, puis push.
- **Release** : bumper `__version__` (+ `pyproject.toml`), commit `chore(release): vX.Y.Z`, poser le tag `vX.Y.Z` (cf. `docs/RELEASE.md`).

## Pour reprendre vite (checklist nouveau PC)

1. `git clone` (ou ouvrir le dossier déjà synchronisé) puis lire ce fichier.
2. Recréer le venv et installer : `.venv/Scripts/python -m pip install -r requirements.txt` (penser à l'exclusion pCloud avant si gros téléchargements).
3. `.venv/Scripts/python -m pytest -q` → doit afficher `615 passed, 1 deselected`.
4. Lancer `.venv/Scripts/python -m anonymator` pour l'UI, ou un `dist/…/*.exe` si un build PyInstaller est disponible.
