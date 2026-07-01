# Éclatement de « Paramètres » en 3 boutons/écrans dédiés

Date : 2026-07-01

## Contexte

L'écran d'accueil propose un unique bouton **Paramètres** qui ouvre un
`SettingsScreen` fourre-tout regroupant : thème, dossier de sortie, types
d'entités à détecter, **règles métier**, modèle de détection GLiNER et un bloc
**À propos** (mentions légales AGPL). L'utilisateur veut séparer la *gestion des
règles* et l'*à propos* dans des boutons — et donc des écrans — dédiés.

## Objectif

Depuis l'accueil, exposer **trois** boutons issus du `SettingsScreen` actuel :

| Bouton accueil (icône) | Écran | Contenu |
|---|---|---|
| **Paramètres** (`settings`) | `SettingsScreen` (allégé) | Thème, dossier de sortie, types d'entités, modèle GLiNER |
| **Gestion des règles** (`shield`) | `RulesScreen` (nouveau) | Règles métier : aide, ligne d'ajout, liste, chemin + « Ouvrir le dossier » |
| **À propos** (`sparkle`) | `AboutScreen` (nouveau) | Mentions légales / licences (`about_lines()`) |

Principe directeur : **déplacer** le code existant (règles, à propos) vers des
écrans dédiés, sans le réécrire ni changer son comportement.

## Découpage en composants

Chaque écran a une responsabilité unique et un `on_back` vers l'accueil,
cohérent avec `TextScreen` / `FileScreen` / `PdfScreen`.

### `anonymator/ui/rules_screen.py` (nouveau)
`RulesScreen(rules_path: Path | None, on_apply, on_back)`.
- Reçoit, déplacés depuis `SettingsScreen` : le bloc « Règles métier » (libellé
  d'aide, ligne d'ajout `rule_pattern`/`rule_mode`/`rule_action`/`rule_note` +
  bouton « Ajouter », `rule_error`, `rules_list`, chemin des règles + bouton
  « Ouvrir le dossier ») et les méthodes `_reload_rules`, `_on_add_rule_clicked`,
  `add_rule`, `remove_rule`, `_open_rules_folder`.
- Charge/sauvegarde `UserRules` via `rules_path` ; appelle `on_apply()` après
  chaque ajout/suppression (comme aujourd'hui) pour que `MainWindow` reconstruise
  le référentiel.
- En-tête `HeaderBand` + bouton « Accueil » (`ghost`) → `on_back`.

### `anonymator/ui/about_screen.py` (nouveau)
`AboutScreen(on_back)`.
- Affiche `"\n".join(about_lines())` dans un label `muted` + en-tête + bouton
  « Accueil ». `anonymator/ui/about.py` (fonction pure) reste inchangé.
- Expose `about_label` pour les tests.

### `anonymator/ui/settings_screen.py` (allégé)
- Retire le bloc « Règles métier » et le bloc « À propos ».
- Supprime le paramètre `rules_path`, les imports `UserRules`/`Rule`/
  `compile_pattern` et `about_lines`, ainsi que les méthodes/attributs déplacés.
- Conserve : thème, dossier de sortie, types d'entités, section modèle GLiNER
  (`model_ready`, téléchargement, `stop_download`, `closeEvent`).

### `anonymator/ui/home_screen.py`
- `HomeScreen.__init__` gagne `on_rules` et `on_about`.
- Deux `NavCard` ajoutées après « Paramètres » :
  - « Gestion des règles » / sous-titre « Règles métier » / icône `shield` →
    `on_rules`.
  - « À propos » / sous-titre « À propos » / icône `sparkle` → `on_about`.
- Sous-titre de « Paramètres » reformulé : « Thème, dossier, types, modèle ».

### `anonymator/ui/main_window.py`
- Instancie `RulesScreen(self.rules_path, self._apply_prefs, self.show_home)` et
  `AboutScreen(self.show_home)` ; les ajoute au `QStackedWidget`.
- Passe `on_rules=self.show_rules` et `on_about=self.show_about` à `HomeScreen`.
- Ajoute `show_rules()` et `show_about()`.
- `SettingsScreen(...)` est instancié sans `rules_path`.
- Inchangé : `_request_model` continue d'ouvrir `SettingsScreen` (le modèle y
  reste), la migration one-shot stoplist→`user_rules.json` dans `_build_ref`.

## Flux

Accueil → clic carte → `stack.setCurrentWidget(<écran>)`. Retour via « Accueil ».
Ajout/suppression de règle dans `RulesScreen` → `on_apply` → `MainWindow`
sauvegarde les prefs et reconstruit `self.ref` depuis `rules_path`, propagé à
`text/file/pdf_screen` (comportement actuel préservé).

## Tests (TDD)

- **`tests/test_rules_screen.py`** (nouveau) : reprend `test_add_and_remove_rule`
  contre `RulesScreen` ; vérifie `keep_matches` après ajout puis suppression.
- **`tests/test_about_screen.py`** (nouveau) : reprend l'assertion de
  `test_settings_shows_about_section` contre `AboutScreen.about_label`
  (AGPL-3.0, version, URL dépôt).
- **`tests/test_settings_screen.py`** : conserve thème / types / modèle ; retire
  la dépendance `rules_path` et l'assertion « à propos ».
- `tests/test_about.py` (fonction pure) : inchangé.
- Ajout possible d'un test de câblage accueil : les cartes `on_rules`/`on_about`
  déclenchent bien le changement d'écran.

## Hors périmètre

- Aucun changement du moteur de détection, des règles métier elles-mêmes, du
  format `user_rules.json` ni des mentions légales.
- Pas de refonte visuelle au-delà de l'ajout des deux cartes.
