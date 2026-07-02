# Design — Refonte visuelle des écrans (Paramètres / Règles / À propos) + nav globale

Date : 2026-07-02

## Contexte

Le design system carte (`Card`, `StatCard`, `NavCard`, `CategoryBadge`, QSS charte :
`#Card`, `#StatCard`, `sectionLabel`, badges…) existe déjà et est utilisé par
l'écran **Accueil** (`home_screen.py`). Trois écrans sont restés en version
« brute » — empilement de `QLabel`/`QComboBox` sans cartes :

- `settings_screen.py` (Paramètres — « Détection & masquage »)
- `rules_screen.py` (Règles métier)
- `about_screen.py` (À propos)

Des maquettes fournies par l'utilisateur montrent ces trois écrans portés sur le
design system (cartes, sections à icône, badges, table de règles, cartes
d'entités). Objectif : réécrire **la présentation** de ces écrans pour être
**fidèle aux maquettes**, sans toucher à la logique métier.

Décision complémentaire validée : le **bandeau d'onglets** (nav) introduit pour
ces écrans est appliqué à **toutes les pages** de l'application.

## Périmètre

**Présentation uniquement.** Aucune modification de :
`referential.py`, `preferences.py`, `user_rules.py`, `model_status.py`,
`download_worker.py`, ni de la logique de détection/masquage.

Fichiers touchés :
- `anonymator/ui/settings_screen.py` — réécriture de la vue
- `anonymator/ui/rules_screen.py` — réécriture de la vue (liste → table)
- `anonymator/ui/about_screen.py` — réécriture de la vue
- `anonymator/ui/components/nav_band.py` — **nouveau** composant nav partagé
- `anonymator/ui/components/rule_action_badge.py` — **nouveau** badge d'action (ou extension de `badge.py`)
- `anonymator/ui/icons.py` — enregistrement des nouvelles icônes
- `anonymator/ui/assets/icons/*.svg` — **nouvelles** icônes
- `anonymator/ui/theme.py` — ajouts QSS ponctuels (onglets, mini-cartes d'entité, table de règles)
- Écrans recevant la nav globale : `home_screen.py`, `text_screen.py`,
  `file_screen.py`, `pdf_screen.py` (insertion du bandeau, sans refonte)
- `main_window.py` — si la nav a besoin d'un point d'ancrage commun (à valider en plan)
- Tests UI à adapter (voir §Tests)

## Composant partagé : bandeau d'onglets (`NavBand`)

Sous le `HeaderBand` (logo + « Anonymator | RÉSEAU CUMA »), un bandeau d'onglets :

- Onglet **« 🏠 Accueil »** (icône `home`) → `on_home()`.
- Onglet du **nom de l'écran actif** (ex. « Détection & masquage »), avec
  soulignement vert (couleur `action`) marquant l'onglet actif.
- Sur l'écran Accueil, l'onglet actif est « Accueil » (pas de second onglet).

API proposée :
```python
NavBand(title: str, icon_name: str, on_home: Callable)
```
Il remplace l'actuelle ligne `nav` (bouton « Accueil » ghost + `QLabel` titre)
présente dans chaque écran. Style via QSS dédié (`#NavBand`, `QPushButton#tab`,
`QPushButton#tabActive`).

Pour Texte/Fichier/PDF : le `NavBand` s'insère **au-dessus** de la barre
d'action existante (`#ActionBand`), sans en modifier le fonctionnement.

## Écran 1 — Paramètres (« Détection & masquage »)

En-tête : icône `settings` + titre « Détection & masquage » + sous-titre
« Réglez le thème, la sortie et ce que l'application repère automatiquement. »

**Carte « GÉNÉRAL »** (icône `palette`) :
- « Thème de l'application » : `QComboBox` avec libellés lisibles mappés sur les
  clés de thème — `CUMA — vert identitaire` → `cuma`, `CAP — bleu` → `cap`.
- « Dossier de sortie » : `QLineEdit` + bouton `Choisir…`.

**Carte « TYPES D'ENTITÉS À DÉTECTER »** (icône `shield`) avec badge
`X / 14 actifs` (mis à jour au toggle) :
- Grille 2 colonnes de mini-cartes `#EntityCard` : icône + nom + sous-titre +
  `ToggleSwitch`. Les **14 types** sont affichés.

| Type | Libellé | Sous-titre | Icône |
|---|---|---|---|
| PERSON | PERSON | Noms et prénoms de personnes | person |
| ADDRESS | ADDRESS | Adresses postales | map-pin |
| ORG | ORG | Organisations, entreprises | building |
| EMAIL | EMAIL | Adresses e-mail | mail |
| PHONE | PHONE | Numéros de téléphone | phone |
| IBAN | IBAN | Coordonnées bancaires | credit-card |
| BIC | BIC | Codes banque · SWIFT | scale |
| SIREN | SIREN | Identifiants d'entreprise | building |
| SIRET | SIRET | Établissements (SIREN + NIC) | building |
| NIR | NIR | Numéro de sécurité sociale | id-card |
| POSTAL_CODE | POSTAL_CODE | Codes postaux | map-pin |
| URL | URL | Adresses web | globe |
| LOGIN | LOGIN | Identifiants de connexion | user |
| PASSWORD | PASSWORD | Mots de passe | lock |

**Carte « MODÈLE DE DÉTECTION INTELLIGENTE »** (icône `cpu`) :
texte explicatif + statut (installé/taille), emplacement, bouton
télécharger/réparer, barre de progression. **Logique de téléchargement
inchangée** — seul l'habillage change.

## Écran 2 — Règles (« Règles métier »)

En-tête : icône `layers` (ou dédiée) + titre « Règles métier » + aide existante.

**Carte barre d'ajout** : `Motif` / `Mode` (simple|expert) / `Action`
(Ne jamais masquer | Toujours masquer) / `Note` / bouton `+ Ajouter`, sur une
ligne stylée. Message d'erreur sous la barre.

**Table « RÈGLES DÉFINIES »** avec badge `N règles` :
- `QTableWidget` colonnes : MOTIF · MODE · ACTION · NOTE · (corbeille).
- MODE en capitales grises (`SIMPLE`/`EXPERT`).
- ACTION : badge vert « 👁 Ne jamais masquer » (keep) / orange
  « 🚫 Toujours masquer » (mask).
- Bouton corbeille (icône `trash`) par ligne → suppression.
- Remplace le `QListWidget` actuel.

**Pied** : chemin du fichier de règles (`muted`) + `Ouvrir le dossier`.

Le mapping mode UI ↔ interne (`simple`/`expert` → `simple`/`regex`) et
`action` (index → `keep`/`mask`) est **inchangé**.

## Écran 3 — À propos

**Héros centré** : logo CUMA (`assets/logo.png`) + « Anonymator » + badge
version (`__version__`) + pitch (« Anonymisez vos textes et fichiers en local… »).

**Carte « LICENCE & CODE SOURCE »** (icône `scale`) :
- AGPL-3.0 — « Logiciel libre — copyleft ».
- Lien GitHub cliquable : `github.com/gudr-perso/Anonymator · tag vX.Y.Z`
  (icône `github`, ouverture via `QDesktopServices`).

**Carte « COMPOSANTS EMBARQUÉS »** (icône `package`) :
- PyMuPDF © Artifex Software · lecture & écriture PDF — badge `AGPL-3.0`.
- GLiNER `urchade/gliner_multi-v2.1` · détection d'entités — badge `Apache-2.0`.

Contenu dérivé de `about_lines()` / constantes de `about.py` (source unique
conforme AGPL — le tag `vX.Y.Z` reste calculé depuis `__version__`).

## Icônes SVG à créer

Style trait cohérent avec l'existant (viewBox 24, stroke, sans remplissage),
teintables par `icons.icon(name, color)`. À ajouter dans `assets/icons/` et à
`ICON_NAMES` :

`person, user, building, map-pin, mail, phone, credit-card, scale, id-card,
globe, lock, eye, trash, palette, cpu, github, package`

(`eye-off`, `home`, `settings`, `shield`, `layers`, `chevron-right` existent.)

## QSS (ajouts `theme.py`)

- `#NavBand`, `QPushButton#tab`, `QPushButton#tabActive` (soulignement `action`).
- `#EntityCard` (mini-carte type), `#EntityCard:hover`.
- Table de règles : réutilise `QTableWidget`/`QHeaderView::section` existants.
- Badge d'action règles (vert/orange) : couleurs `action`/`accent` teintées.

## Tests

Adapter les tests UI existants qui ciblent la structure actuelle :
- `tests/test_settings_screen.py`
- `tests/test_rules_screen.py`
- `tests/test_about_screen.py` / `test_about.py`
- `tests/test_home_screen.py`, `test_ui_smoke.py`, `test_main_window_pdf.py`
  (si la nav globale change des accroches de widgets)

Principe : les tests vérifient le **comportement** (toggle → override, ajout/
suppression de règle → persistance, lien version), pas le pixel. Mettre à jour
les sélecteurs de widgets si besoin ; ajouter un test de présence du `NavBand`
et du badge `X / 14 actifs`.

## Hors périmètre (YAGNI)

- Pas de nouveau thème, pas de refonte de l'écran Accueil (seul le `NavBand`
  s'y ajoute), pas de changement de la logique de détection/masquage,
  pas de nouvelles entités détectables.
