# Anonymator — État du projet & comment continuer

> Point de reprise. Lis ce fichier en premier quand tu rouvres le projet (y compris depuis un autre PC).
> Dernière mise à jour : 2026-07-09.

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
| **Conformité AGPL + versionnage taggé** (déclenché par PyMuPDF) | ✅ **Fait** — `LICENSE` AGPL-3.0, tags `v0.2.0` → `v0.4.1` posés |
| **Support PDF** (rédaction juridique réelle + extraction texte) | ✅ **Fait — `v0.2.0`** (PyMuPDF, revue visuelle, propagation, ordre de lecture) |
| **Règles métier utilisateur** (allow/force par motif, `[REGLE-INTERNE]`) | ✅ **Fait** — écran « Gestion des règles » dédié |
| **Éclatement des Paramètres** (Paramètres / Gestion des règles / À propos) | ✅ **Fait** |
| **Refonte des écrans + refonte thème CAP** | ✅ **Fait** |
| **Anonymisation Office (.docx / .pptx)** + purge métadonnées | ✅ **Fait — `v0.3.0`** |
| **Marques verrouillées CAP / CUMA** (thème figé, nom produit, sélecteur masqué) | ✅ **Fait — `v0.4.0`** (build paramétré par marque) |
| **Landing page Cum'Anonyme** (`html/index.html`, autonome) | ✅ **Fait** — lien de DL vers `cap-consulting.org/_dl` |
| Test d'intégration GLiNER (modèle réel) | ⬜ **Jamais lancé** (voir `docs/installation-gliner.md`) |
| Installeur Windows (setup.exe + raccourcis + code signing) | ⬜ **Pas commencé** — « Plan 5 » (brainstorming dédié à faire) |

**Tests : 478 verts + 1 d'intégration déselectionné** (`.venv/Scripts/python -m pytest -q` → `478 passed, 1 deselected`).
Le test d'intégration ne nécessite `torch` que si on lance `-m integration`.

**Version courante : `0.4.1`** (`anonymator/__init__.py` = source de vérité, dupliquée dans `pyproject.toml`).

## Prochaine action

Le gros du produit est livré (texte, csv/xlsx, PDF, docx/pptx, règles métier, deux marques, landing page).
Pistes ouvertes, par ordre de valeur :

1. **Installeur Windows** (« Plan 5 ») : brainstorming dédié — `setup.exe` (Inno Setup ?), raccourcis menu Démarrer,
   éventuel **code signing**, mise à jour. Un seul installeur par marque (réutilise `scripts/build.ps1` qui zippe déjà par marque).
2. **Validation manuelle des exes des deux marques** : dérouler le scénario GLiNER « zéro friction » (démarrage sans
   modèle → mode dégradé → téléchargement guidé) sur `dist/…/*.exe`, et vérifier le verrou de thème (sélecteur masqué).
3. **Diffusion de la landing page** : déposer `html/index.html` sur l'hébergement et brancher le vrai binaire derrière
   `cap-consulting.org/_dl`.
4. **Test d'intégration GLiNER** (modèle réel) : toujours jamais exécuté (`docs/installation-gliner.md`).

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
  user_rules.py       règles métier utilisateur (keep/mask par motif, mode simple/regex)
  pipeline.py         detect(text, ner, ref) : déterministe ∥ NER -> merge
  anonymize.py        apply_masking(text, entities, ref) -> texte [CATÉGORIE]
  output_naming.py    <nom>_ano_AAAAMMJJHHMMSS.<ext>
  brand.py            marque = surcouche thème + nom produit (CAP / CUMA / dev)
  brands/             cap.py, cuma.py : points d'entrée verrouillés (build paramétré)
  files/              encoding, csv_io, columns, txt_io, xlsx_io, anonymize_file (orchestrateur + dispatcher)
    pdf/              pdf_io, extract, mapping, redact (caviardage réel PyMuPDF), render, propagate
    ooxml/            docx_io, pptx_io, scan, run_remap, text_unit, xml_parts, metadata (purge)
  report/audit.py     AuditReport (agrégation + export CSV/JSON)
  core/               model_status (dispo/taille cache GLiNER), model_download (DL HuggingFace + progression)
  ui/                 PySide6 : main_window (démarrage non bloquant, thème piloté par marque),
                      home_screen (bandeau d'onglets, repli logo par marque), settings_screen (allégé),
                      rules_screen (gestion des règles), about_screen / about (mentions AGPL + contact),
                      text_screen, file_screen, pdf_screen + pdf_canvas (aperçu image + overlays + zoom),
                      workers QThread (text_analyze, file_scan/anonymize, ooxml_scan, pdf_scan, download),
                      model_loader, preferences, colors, entity_meta, icons, theme, components/
tests/                un fichier de test par module (TDD) — 91 fichiers, 478 tests verts
html/index.html       landing page Cum'Anonyme (autonome, CSS inline, logos base64)
scripts/              build.ps1 (build + zip par marque), make_ico.py
docs/                 ETAT-PROJET.md (ce fichier), DOCUMENTATION.md, RELEASE.md, installation-gliner.md,
  superpowers/        specs/ (conception + journal) et plans/ (1-4, GLiNER, PDF, règles, docx/pptx, marques…)
```

## Décisions verrouillées (rappel)

- **v1 = anonymisation seule** ; pseudonymisation / relais Anthropic / vault = v2.
- Détection floue = **GLiNER** (pas Ollama) ; substitution **déterministe** (« le code dispose »).
- **Deux marques diffusées, thème verrouillé** : **Cum'Anonyme** (CUMA vert) et **CAP'nonyme** (CAP bleu).
  L'exe force son thème et **masque le sélecteur** (verrou UI seulement ; les 2 thèmes restent dans le binaire).
  Un mode **dev** non verrouillé garde le sélecteur (non diffusé). Titres Space Grotesk, texte Inter.
- Couleurs **fonctionnelles** par type d'entité = jeu **fixe** (indépendant du thème).
- **BIC** et **code postal** implémentés mais **inactifs par défaut** (bruyants sur FEC ; activables).
- **ORG masqué par défaut** (banques incluses).
- **Règles métier utilisateur** : moteur **symétrique** `keep` (allow-list) / `mask` (force-list → `[REGLE-INTERNE]`),
  par **motif** (simple avec jokers, ou regex expert), éditables **sans toucher au code** et **partageables**.
- **GLiNER non bloquant** : l'app démarre toujours ; sans le modèle → **mode dégradé** (règles déterministes seules +
  bannière). Téléchargement guidé (barre % réelle) depuis l'accueil ou Paramètres ; reprise sans redémarrage.
- **GLiNER tronque > ~384 tokens** : découper le texte **avant** le NER (piège rencontré sur PDF).
- **Exe windowed** : `sys.stdout`/`sys.stderr` sont `None` → garde-fou dans `anonymator/__main__.py`.
- **PDF** : PDF **natifs uniquement** (scannés refusés, OCR plus tard), **2 modes** (rédaction juridique = destruction
  réelle via PyMuPDF + extraction texte), **revue visuelle obligatoire** avant destruction ; propagation tout-document
  des valeurs confirmées + ordre de lecture. PyMuPDF isolé dans `anonymator/files/pdf/`.
- **Office .docx/.pptx** : remap mutualisé, **revue par liste d'entités** (pas de rendu visuel), couverture cœur +
  périphérique, **purge systématique des métadonnées** d'identité tracée dans l'audit.
- **Licence** : **AGPL-3.0** (imposé par PyMuPDF) → repo public + `LICENSE` AGPL ; **pas** de licence commerciale
  Artifex. Versionnage : **tag `vX.Y.Z` par release**, pas par commit ; `__version__` unique lu par l'UI.
  GLiNER `urchade/gliner_multi-v2.1` = Apache-2.0 (usage commercial OK).

---

## Environnement & pièges (IMPORTANT sur un nouveau PC)

- **Python** : sur la machine d'origine, `python`/`python3` sont des stubs Windows Store → toujours `.venv/Scripts/python`. Sur un autre PC, vérifier l'interpréteur ; recréer le venv si besoin :
  `python -m venv .venv` puis `.venv/Scripts/python -m pip install -r requirements.txt`.
- **Le `.venv/` n'est pas dans git** (voir `.gitignore`). À recréer sur chaque machine.
- **pCloud + grosses dépendances** : `torch` (via gliner) et `PySide6` pèsent des centaines de Mo. Avant de les installer, **exclure `.venv/` de la synchro pCloud** (ou créer le venv hors du dossier pCloud). Détails : `docs/installation-gliner.md`.
- **`.git` synchronisé par pCloud** : branche/historique/fichiers peuvent changer en cours de session → vérifier l'état (`git status`, `git log`) avant de committer.
- **Lancer les tests** : `.venv/Scripts/python -m pytest -q` (→ `478 passed, 1 deselected`). Plateforme offscreen gérée automatiquement via `tests/conftest.py`.
- **Lancer l'appli** : `.venv/Scripts/python -m anonymator` (mode dev, sélecteur de thème actif).
- **Builder les exes** : `scripts/build.ps1` (spec paramétré par `ANONYMATOR_BUILD_BRAND`, zippe par marque, copie le `LICENSE` à la racine du dossier distribué).

## Git / remote

- Remote : `https://github.com/gudr-perso/Anonymator.git`, branche `main`.
- **Pousser** : sur la machine d'origine, le compte git par défaut (`gudr-cuma`) n'a pas les droits → l'URL du remote embarque `gudr-perso@` pour forcer le bon jeton. **Sur un autre PC**, configurer l'authentification GitHub du compte **gudr-perso** (sinon `403`). Si besoin :
  `git remote set-url origin https://gudr-perso@github.com/gudr-perso/Anonymator.git`
- Convention : une branche `feat/...` par plan, fusion dans `main` après revue, puis push.
- **Release** : bumper `__version__` (+ `pyproject.toml`), commit `chore(release): vX.Y.Z`, poser le tag `vX.Y.Z` (cf. `docs/RELEASE.md`).

## Pour reprendre vite (checklist nouveau PC)

1. `git clone` (ou ouvrir le dossier déjà synchronisé) puis lire ce fichier.
2. Recréer le venv et installer : `.venv/Scripts/python -m pip install -r requirements.txt` (penser à l'exclusion pCloud avant si gros téléchargements).
3. `.venv/Scripts/python -m pytest -q` → doit afficher `478 passed, 1 deselected`.
4. Lancer `.venv/Scripts/python -m anonymator` pour l'UI, ou un `dist/…/*.exe` si un build PyInstaller est disponible.
