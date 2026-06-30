# Anonymator — État du projet & comment continuer

> Point de reprise. Lis ce fichier en premier quand tu rouvres le projet (y compris depuis un autre PC).
> Dernière mise à jour : 2026-06-30.

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
| Test d'intégration GLiNER (modèle réel) | ⬜ **Jamais lancé** (voir `docs/installation-gliner.md`) |

**Tests : 101 verts + 1 d'intégration déselectionné** (ne nécessite PAS torch tant qu'on ne lance pas `-m integration`).

## Prochaine action

**Lancer le test d'intégration GLiNER** (cf. `docs/installation-gliner.md`) pour valider la détection avec le vrai modèle.
Ensuite : envisager Plan 5 (icône exe, code signing, NSIS installer) ou tester l'exe sur une autre machine.

Méthode utilisée jusqu'ici : skill `superpowers:subagent-driven-development` (un sous-agent par tâche, revue conformité + qualité, branche dédiée puis fusion).

---

## Carte du code (sur `main`)

```
anonymator/
  model.py            Entity (dataclass span)
  validators.py       Luhn, IBAN mod97, NIR, BIC (pays ISO), code postal FR
  deterministic.py    détecteurs regex+checksum -> Entities
  merge.py            résolution des chevauchements (déterministe > confiance > longueur)
  ner.py              NerDetector (protocole), FakeNer (tests), GlinerDetector (réel, import torch paresseux)
  dedup.py            détecte une fois par valeur unique
  referential.py      référentiel JSON (anonymator/config/entities.json)
  pipeline.py         detect(text, ner, ref) : déterministe ∥ NER -> merge
  anonymize.py        apply_masking(text, entities, ref) -> texte [CATÉGORIE]
  output_naming.py    <nom>_ano_AAAAMMJJHHMMSS.<ext>
  files/              encoding, csv_io (sniff robuste virgules décimales), columns (règle D),
                      txt_io, xlsx_io (openpyxl en place), anonymize_file (orchestrateur + dispatcher)
  report/audit.py     AuditReport (agrégation + export CSV/JSON)
tests/                un fichier de test par module (TDD)
docs/superpowers/     specs/ (conception + journal) et plans/ (1, 2, 3, 4)
```

## Décisions verrouillées (rappel)

- **v1 = anonymisation seule** ; pseudonymisation / relais Anthropic / vault = v2.
- Détection floue = **GLiNER** (pas Ollama) ; substitution **déterministe** (« le code dispose »).
- **Thèmes** : CAP (bleu) + CUMA (vert), commutables ; **défaut CUMA**. Titres Space Grotesk, texte Inter.
- Couleurs **fonctionnelles** par type d'entité = jeu **fixe** (indépendant du thème).
- **BIC** et **code postal** implémentés mais **inactifs par défaut** (bruyants sur FEC ; activables).
- **ORG masqué par défaut** (banques incluses).
- PDF = piste pour version ultérieure (module caviardage/OCR dédié), hors v1.

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
