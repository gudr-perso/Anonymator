# Anonymator — État du projet & comment continuer

> Point de reprise. Lis ce fichier en premier quand tu rouvres le projet (y compris depuis un autre PC).
> Dernière mise à jour : 2026-07-01.

---

## Où on en est

Application locale Windows d'**anonymisation** (non réversible) de texte et de fichiers comptables.
Développement piloté par specs + plans, en TDD, exécution par sous-agents avec revue.

| Étape | État |
|---|---|
| **Plan 1 — moteur de détection & anonymisation texte** | ✅ **Fait, fusionné dans `main`** |
| **Plan 2 — E/S fichiers (txt/csv/xlsx) + rapport d'audit** | ✅ **Fait, fusionné dans `main`** |
| **Plan 3 — application UI PySide6** | ✅ **Fait, fusionné dans `main`** |
| **Plan 4 — packaging PyInstaller + README + 1er téléchargement modèle** | ✅ **Fait, sur `main`** |
| **Expérience GLiNER « zéro friction » (non bloquant + mode dégradé)** | ✅ **Fait, fusionné dans `main`** |
| Test d'intégration GLiNER (modèle réel) | ⬜ **Jamais lancé** (voir `docs/installation-gliner.md`) |
| **Support PDF (rédaction juridique + extraction texte)** | 🟡 **Design validé, plan à écrire** — spec [2026-07-01-support-pdf-design.md](superpowers/specs/2026-07-01-support-pdf-design.md) |
| **Conformité AGPL + versionnage** (déclenché par PyMuPDF) | 🟡 **Design validé, à implémenter** — spec [2026-07-01-conformite-agpl-design.md](superpowers/specs/2026-07-01-conformite-agpl-design.md) |

**Tests : 194 verts + 1 d'intégration déselectionné** (ne nécessite PAS torch tant qu'on ne lance pas `-m integration`).

## Prochaine action

**Chantier PDF** (brainstorming terminé le 2026-07-01, 2 specs validés et poussés) :
1. Écrire le **plan d'implémentation** du support PDF (skill `superpowers:writing-plans`) à partir du
   spec [2026-07-01-support-pdf-design.md](superpowers/specs/2026-07-01-support-pdf-design.md).
2. **Deux points ouverts à trancher avant/pendant le plan** :
   - écran PDF **dédié** vs extension de `FileScreen` (le canevas image + overlays diffère du tableau CSV) ;
   - **sélection de zone manuelle** (caviarder un tampon/signature non détecté) : *non* incluse en v1 par défaut —
     si on la veut, ça change le canevas, à décider maintenant.
3. ~~En parallèle et indépendant : implémenter la **conformité AGPL**~~ **✅ FAIT** (branche
   `feat/conformite-agpl`, plan [2026-07-01-conformite-agpl.md](superpowers/plans/2026-07-01-conformite-agpl.md)) :
   `LICENSE` AGPL-3.0 (racine + embarqué dans le zip via `.spec`), SPDX dans `pyproject.toml`, section
   « À propos » dans les Paramètres (`anonymator/ui/about.py` + `settings_screen`), section Licence du README,
   `__version__` unique lu par l'UI (sans git au runtime) + garde-fou de synchro, procédure de release
   [docs/RELEASE.md](RELEASE.md). Licence GLiNER tranchée : `urchade/gliner_multi-v2.1` = Apache-2.0 (usage
   commercial OK). **Reste à faire** (validation manuelle) : poser un vrai tag `vX.Y.Z` et démontrer la
   correspondance exe ↔ tag ↔ source (cf. `docs/RELEASE.md`).

Rappel modèle : Anonymator devient **open source AGPL-3.0** (repo public) à cause de PyMuPDF ; monétisation par
**prestation** (install/formation/support), pas par vente de licence/clé (inopposable en AGPL).

Autres pistes en attente : **installeur Windows** (setup.exe + raccourcis + code signing — brainstorming dédié,
« Plan 5 »), validation manuelle de l'exe (scénario GLiNER zéro friction).

Méthode utilisée jusqu'ici : skill `superpowers:subagent-driven-development` (un sous-agent par tâche, revue conformité + qualité, branche dédiée puis fusion).

---

## Carte du code (sur `main`)

```
anonymator/
  model.py            Entity (dataclass span)
  validators.py       Luhn, IBAN mod97, NIR, BIC (pays ISO), code postal FR
  deterministic.py    détecteurs regex+checksum -> Entities
  merge.py            résolution des chevauchements (déterministe > confiance > longueur)
  ner.py              NerDetector (protocole), FakeNer (tests), NullNer (mode dégradé), GlinerDetector (réel, torch paresseux)
  dedup.py            détecte une fois par valeur unique
  referential.py      référentiel JSON (anonymator/config/entities.json)
  pipeline.py         detect(text, ner, ref) : déterministe ∥ NER -> merge
  anonymize.py        apply_masking(text, entities, ref) -> texte [CATÉGORIE]
  output_naming.py    <nom>_ano_AAAAMMJJHHMMSS.<ext>
  files/              encoding, csv_io (sniff robuste virgules décimales), columns (règle D),
                      txt_io, xlsx_io (openpyxl en place), anonymize_file (orchestrateur + dispatcher)
  report/audit.py     AuditReport (agrégation + export CSV/JSON)
  core/model_status.py    disponibilité + taille du modèle GLiNER en cache (non-Qt)
  core/model_download.py  téléchargement HuggingFace avec progression agrégée (non-Qt)
  ui/                 PySide6 : main_window (démarrage non bloquant + orchestration modèle),
                      home_screen (carte d'invite), settings_screen (section « Modèle de détection »),
                      text_screen / file_screen (mode dégradé + bannière), download_worker (QThread),
                      components/ (banner, cards, header, toggle, badge)
tests/                un fichier de test par module (TDD)
docs/superpowers/     specs/ (conception + journal, dont support-pdf & conformité-agpl 2026-07-01)
                      et plans/ (1-4 + expérience GLiNER ; plan PDF à écrire)
```

## Décisions verrouillées (rappel)

- **v1 = anonymisation seule** ; pseudonymisation / relais Anthropic / vault = v2.
- Détection floue = **GLiNER** (pas Ollama) ; substitution **déterministe** (« le code dispose »).
- **Thèmes** : CAP (bleu) + CUMA (vert), commutables ; **défaut CUMA**. Titres Space Grotesk, texte Inter.
- Couleurs **fonctionnelles** par type d'entité = jeu **fixe** (indépendant du thème).
- **BIC** et **code postal** implémentés mais **inactifs par défaut** (bruyants sur FEC ; activables).
- **ORG masqué par défaut** (banques incluses).
- **GLiNER non bloquant** : l'app démarre toujours ; sans le modèle → **mode dégradé** (règles déterministes seules + bannière). Téléchargement guidé (barre % réelle) depuis l'accueil ou Paramètres ; reprise sans redémarrage.
- **Exe windowed** : `sys.stdout`/`sys.stderr` sont `None` → garde-fou dans `anonymator/__main__.py` (sinon `tqdm`/libs plantent avec `'NoneType' object has no attribute 'write'`).
- **PDF** (design validé 2026-07-01) : PDF **natifs uniquement** en v1 (scannés refusés, OCR plus tard), **2 modes** (rédaction juridique = destruction réelle via PyMuPDF + extraction texte), **revue visuelle obligatoire** avant destruction. PyMuPDF isolé dans `anonymator/files/pdf/`.
- **Licence** : passage en **AGPL-3.0** (imposé par PyMuPDF) → repo public + `LICENSE` AGPL ; **pas** de licence commerciale Artifex (closed source seulement). Versionnage : **tag `vX.Y.Z` par release**, pas par commit, `__version__` unique lu par l'UI.

---

## Environnement & pièges (IMPORTANT sur un nouveau PC)

- **Python** : sur la machine d'origine, `python`/`python3` sont des stubs Windows Store → toujours `.venv/Scripts/python`. Sur un autre PC, vérifier l'interpréteur ; recréer le venv si besoin :
  `python -m venv .venv` puis `.venv/Scripts/python -m pip install -r requirements.txt`.
- **Le `.venv/` n'est pas dans git** (voir `.gitignore`). À recréer sur chaque machine.
- **pCloud + grosses dépendances** : `torch` (via gliner) et `PySide6` pèsent des centaines de Mo. Avant de les installer, **exclure `.venv/` de la synchro pCloud** (ou créer le venv hors du dossier pCloud). Détails : `docs/installation-gliner.md`.
- **Lancer les tests** : `.venv/Scripts/python -m pytest -q` (101 verts, 1 intégration déselectionné). Plateforme offscreen gérée automatiquement via `tests/conftest.py`.
- **Lancer l'appli** (après Plan 3) : `.venv/Scripts/python -m anonymator`.

## Git / remote

- Remote : `https://github.com/gudr-perso/Anonymator.git`, branche `main`.
- **Pousser** : sur la machine d'origine, le compte git par défaut (`gudr-cuma`) n'a pas les droits → l'URL du remote embarque `gudr-perso@` pour forcer le bon jeton. **Sur un autre PC**, configurer l'authentification GitHub du compte **gudr-perso** (sinon `403`). Si besoin :
  `git remote set-url origin https://gudr-perso@github.com/gudr-perso/Anonymator.git`
- Convention : une branche `feat/...` par plan, fusion dans `main` après revue, puis push.

## Pour reprendre vite (checklist nouveau PC)

1. `git clone` (ou ouvrir le dossier déjà synchronisé) puis lire ce fichier.
2. Recréer le venv et installer : `.venv/Scripts/python -m pip install -r requirements.txt` (penser à l'exclusion pCloud avant si gros téléchargements).
3. `.venv/Scripts/python -m pytest -q` → doit afficher 101 passed, 1 deselected.
4. Lancer `.venv/Scripts/python -m anonymator` pour l'UI, ou `dist/anonymator/anonymator.exe` si le build PyInstaller est disponible.
