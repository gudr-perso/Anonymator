# Conformité AGPL & stratégie de versionnage — Design

> **Statut** : à traiter (indépendant du chantier PDF).
> **Déclencheur** : l'introduction de PyMuPDF (dépendance AGPL-3.0) pour le support PDF
> impose de mettre Anonymator en conformité AGPL. Ce spec regroupe les tâches de
> conformité et fixe la stratégie de versionnage, prérequis de la clause « source =
> binaire livré ».
>
> ⚠️ Ceci n'est pas un avis juridique : c'est la mécanique de l'AGPL-3.0 telle
> qu'appliquée à une application desktop distribuée.

---

## 1. Contexte & décision

Anonymator embarquera **PyMuPDF** (éditeur Artifex), doublement licencié
**AGPL-3.0 / commercial**. Modèle de distribution retenu :

- **Repo GitHub public** + code sous **AGPL-3.0** → usage de PyMuPDF **gratuit et conforme**.
- Modèle économique : **prestation** (installation, formation, support, adaptations
  métier) facturée librement ; le logiciel peut être vendu, mais le client reçoit les
  4 libertés AGPL (dont la redistribution). Pas de verrou par clé (inopposable en AGPL).
- Protection du canal commercial via la **marque** (nom/logo « Anonymator »), pas via le code.

La licence commerciale PyMuPDF (payante, ~1 500–50 000 $) n'est nécessaire **que** si
l'app devait être distribuée en closed source — hors périmètre.

---

## 2. Périmètre

Trois livrables de conformité + une stratégie de versionnage :

1. **Fichier `LICENSE`** — AGPL-3.0.
2. **Écran « À propos »** — mention licence + source + attribution PyMuPDF.
3. **Mention README** — licence et disponibilité du source.
4. **Stratégie de versionnage** — source de vérité unique, tags de release.

Hors périmètre : dépôt de marque (démarche administrative externe), audit de licence
du modèle GLiNER (noté pour plus tard — certains poids sont `cc-by-nc`).

---

## 3. Détail des livrables

### 3.1 Fichier `LICENSE`

- Texte intégral de l'**AGPL-3.0** (source : gnu.org) à la racine du repo.
- Déclarer la licence dans `pyproject.toml` : `license = "AGPL-3.0-or-later"` (SPDX).
- Le fichier `LICENSE` doit être **inclus dans le zip de distribution** (pas seulement
  dans le repo) — ~35 Ko, à ajouter aux `datas` de `anonymator.spec`.

### 3.2 Écran « À propos »

- Ajouter/compléter un écran ou une section « À propos » dans l'UI affichant :
  - `Anonymator v<X.Y.Z>` (lu depuis la source de vérité, cf. §3.4)
  - `Licence : AGPL-3.0 — code source : <URL repo> (tag v<X.Y.Z>)`
  - `Embarque PyMuPDF © Artifex Software — AGPL-3.0`
  - `Embarque GLiNER (<licence à confirmer>)`
- La mention du **tag exact** est ce qui satisfait la correspondance « source = binaire »
  exigée par l'AGPL art. 6. Elle doit refléter la version réellement buildée.
- Emplacement pressenti : écran Paramètres (`settings_screen.py`) ou un bouton
  « À propos » dédié — à trancher au moment de l'implémentation selon l'UI existante.

### 3.3 Mention README

- Section « Licence » dans `README.md` :
  - Licence AGPL-3.0, lien vers `LICENSE`.
  - « Le code source complet est disponible sur `<URL repo>`. Chaque version distribuée
    correspond à un tag `vX.Y.Z`. »
  - Attribution PyMuPDF (Artifex, AGPL-3.0).
- Mettre à jour le tableau des formats (le PDF passera de ❌ à ✅ lors du chantier PDF —
  synchronisation à prévoir, pas dans ce spec).

---

## 4. Stratégie de versionnage

**Problème posé** : ne pas incrémenter un numéro de version à chaque commit, tout en
garantissant la correspondance AGPL « binaire livré ↔ source publié ».

### 4.1 Principe

- **SemVer** : `MAJOR.MINOR.PATCH`.
- **Source de vérité unique** : `__version__ = "X.Y.Z"` dans `anonymator/__init__.py`
  (ou un `anonymator/_version.py` dédié).
- **Bump uniquement à la release**, jamais par commit. Les commits intermédiaires
  n'ont pas de version.
- **Un tag git `vX.Y.Z`** posé sur le commit de release. Le tag = la preuve de
  correspondance source/binaire. Seuls les commits **distribués** sont taggés.
- L'écran « À propos » lit `__version__` (pas de dépendance à git au runtime — important
  car l'exe PyInstaller gelé n'a pas accès à git).

### 4.2 Flux de release

1. Développement libre sur `main` (commits non versionnés).
2. Au moment de distribuer : bump `__version__` → commit `chore(release): vX.Y.Z`.
3. `git tag vX.Y.Z` sur ce commit.
4. Build PyInstaller **depuis ce commit taggé** → l'exe affiche `vX.Y.Z`, le repo
   public contient le source correspondant au même tag. ✅ Conformité AGPL.

### 4.3 Builds de développement (optionnel)

- Un build hors release peut afficher `X.Y.Z-dev` pour éviter toute confusion avec une
  version distribuée. **Seuls les builds issus d'un tag sont distribués.**

### 4.4 Règles de bump (indicatif)

- `PATCH` : corrections sans changement de comportement visible.
- `MINOR` : nouvelle fonctionnalité rétro-compatible (ex. support PDF → `MINOR`).
- `MAJOR` : rupture (changement de format de sortie, d'UI majeure…).

---

## 5. Critères d'acceptation

- [ ] `LICENSE` (AGPL-3.0) présent à la racine **et** embarqué dans le zip distribué.
- [ ] `pyproject.toml` déclare la licence SPDX.
- [ ] Écran « À propos » affiche version + licence + URL source + tag + attribution PyMuPDF.
- [ ] `README.md` comporte une section Licence conforme.
- [ ] `__version__` unique dans le package, lu par l'UI, sans dépendance git au runtime.
- [ ] Procédure de release documentée (bump → tag → build depuis le tag).
- [ ] Une release de test (`vX.Y.Z`) démontre la correspondance exe ↔ tag ↔ source public.

---

## 6. Points ouverts

- Emplacement exact de la mention « À propos » dans l'UI (écran dédié vs section Paramètres).
- Licence effective du modèle GLiNER téléchargé (à auditer séparément).
- Dépôt de marque « Anonymator » (démarche INPI hors code) — décision business.
