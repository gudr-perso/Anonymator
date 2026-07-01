# Éclatement de « Paramètres » en 3 écrans — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Éclater l'écran fourre-tout « Paramètres » en trois boutons/écrans dédiés depuis l'accueil : Paramètres (thème, dossier, types, modèle), Gestion des règles (règles métier), À propos (mentions légales).

**Architecture:** Extraire deux écrans (`RulesScreen`, `AboutScreen`) du `SettingsScreen` actuel en **déplaçant** le code existant sans le réécrire. Les trois écrans sont des enfants du `QStackedWidget` de `MainWindow`, chacun avec un bouton « Accueil ». L'accueil (`HomeScreen`) gagne deux `NavCard`.

**Tech Stack:** Python, PySide6 (Qt), pytest + pytest-qt (`qtbot`).

---

## File Structure

- Create: `anonymator/ui/rules_screen.py` — `RulesScreen`, éditeur de règles métier (déplacé de `SettingsScreen`).
- Create: `anonymator/ui/about_screen.py` — `AboutScreen`, mentions légales (`about_lines()`).
- Modify: `anonymator/ui/settings_screen.py` — retire règles + à propos + param `rules_path`.
- Modify: `anonymator/ui/home_screen.py` — ajoute `on_rules`/`on_about` + 2 `NavCard`.
- Modify: `anonymator/ui/main_window.py` — instancie/câble les nouveaux écrans.
- Create: `tests/test_rules_screen.py` — ajout/suppression de règle.
- Create: `tests/test_about_screen.py` — contenu mentions légales.
- Modify: `tests/test_settings_screen.py` — retire règles + à propos.

Ordre : on crée d'abord les écrans extraits (Tasks 1-2), puis on allège `SettingsScreen` (Task 3), puis on câble l'accueil et `MainWindow` (Tasks 4-5).

---

## Task 1: Écran « Gestion des règles » (`RulesScreen`)

**Files:**
- Create: `anonymator/ui/rules_screen.py`
- Test: `tests/test_rules_screen.py`

Le code des règles vient de `anonymator/ui/settings_screen.py` (bloc « Règles métier »
lignes ~62-95 et méthodes `_reload_rules`, `_on_add_rule_clicked`, `add_rule`,
`remove_rule`, `_open_rules_folder`). On le déplace en l'adaptant à un écran autonome.

- [ ] **Step 1: Écrire le test qui échoue**

Fichier `tests/test_rules_screen.py` :

```python
from anonymator.ui.rules_screen import RulesScreen
from anonymator.user_rules import UserRules


def test_add_and_remove_rule(qtbot, tmp_path):
    rules_path = tmp_path / "user_rules.json"
    UserRules([]).save(rules_path)
    applied = []
    s = RulesScreen(rules_path=rules_path,
                    on_apply=lambda: applied.append(True),
                    on_back=lambda: None)
    qtbot.addWidget(s)
    s.add_rule(mode="simple", pattern="FACT#######", action="keep", note="factures")
    assert s.user_rules.keep_matches("FACT1234567")
    assert applied  # on_apply déclenché → MainWindow reconstruit le référentiel
    rule = s.user_rules.rules[0]
    s.remove_rule(rule)
    assert not s.user_rules.keep_matches("FACT1234567")


def test_invalid_regex_shows_error(qtbot, tmp_path):
    rules_path = tmp_path / "user_rules.json"
    UserRules([]).save(rules_path)
    s = RulesScreen(rules_path=rules_path, on_apply=lambda: None, on_back=lambda: None)
    qtbot.addWidget(s)
    s.add_rule(mode="regex", pattern="[unclosed", action="mask", note="")
    assert "invalide" in s.rule_error.text().lower()
    assert not s.user_rules.rules


def test_rule_persisted_to_disk(qtbot, tmp_path):
    # reprend la couverture de test_ui_smoke::test_settings_screen_adds_and_persists_rule
    rules_path = tmp_path / "user_rules.json"
    UserRules([]).save(rules_path)
    s = RulesScreen(rules_path=rules_path, on_apply=lambda: None, on_back=lambda: None)
    qtbot.addWidget(s)
    s.add_rule(mode="simple", pattern="A#######", action="keep", note="codes internes")
    reloaded = UserRules.load(rules_path)
    assert reloaded.keep_matches("A0000015")
    assert s.rules_path_label.text().find("user_rules.json") != -1
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_rules_screen.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.ui.rules_screen'`.

- [ ] **Step 3: Créer `RulesScreen`**

Fichier `anonymator/ui/rules_screen.py` (code déplacé depuis `SettingsScreen`) :

```python
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QLineEdit,
                               QListWidget, QListWidgetItem)
from anonymator.ui.components.header import HeaderBand
from anonymator.user_rules import UserRules, Rule, compile_pattern


class RulesScreen(QWidget):
    def __init__(self, rules_path: Path | None, on_apply, on_back):
        super().__init__()
        self.rules_path = rules_path
        self.on_apply = on_apply
        self.user_rules = UserRules.load(rules_path) if rules_path else UserRules([])

        root = QVBoxLayout(self)
        root.addWidget(HeaderBand())
        nav = QHBoxLayout()
        back = QPushButton("Accueil"); back.setObjectName("ghost")
        back.clicked.connect(on_back)
        nav.addWidget(back); nav.addWidget(QLabel("Gestion des règles")); nav.addStretch()
        root.addLayout(nav)

        root.addWidget(QLabel("Règles métier"))
        help_rules = QLabel(
            "Définissez vos propres règles. « Ne jamais masquer » protège une "
            "codification interne (ex. A####### = A + 7 chiffres, FACT.* = "
            "convention de nommage). « Toujours masquer » remplace par "
            "[REGLE-INTERNE]. Mode simple : # = un chiffre, ? = un caractère, "
            "* = n'importe quoi. Mode expert : expression régulière.")
        help_rules.setWordWrap(True); help_rules.setObjectName("muted")
        root.addWidget(help_rules)

        add_rule_row = QHBoxLayout()
        self.rule_pattern = QLineEdit(); self.rule_pattern.setPlaceholderText("Motif, ex. A#######")
        self.rule_mode = QComboBox(); self.rule_mode.addItems(["simple", "expert"])
        self.rule_action = QComboBox(); self.rule_action.addItems(["Ne jamais masquer", "Toujours masquer"])
        self.rule_note = QLineEdit(); self.rule_note.setPlaceholderText("Note (optionnel)")
        btn_add_rule = QPushButton("Ajouter"); btn_add_rule.setObjectName("secondary")
        btn_add_rule.clicked.connect(self._on_add_rule_clicked)
        for w in (self.rule_pattern, self.rule_mode, self.rule_action, self.rule_note, btn_add_rule):
            add_rule_row.addWidget(w)
        root.addLayout(add_rule_row)
        self.rule_error = QLabel(""); self.rule_error.setObjectName("muted")
        root.addWidget(self.rule_error)
        self.rules_list = QListWidget(); root.addWidget(self.rules_list)

        path_row = QHBoxLayout()
        self.rules_path_label = QLabel(
            f"Fichier des règles : {self.rules_path}" if self.rules_path
            else "Fichier des règles : (non défini)")
        self.rules_path_label.setObjectName("muted"); self.rules_path_label.setWordWrap(True)
        btn_open = QPushButton("Ouvrir le dossier"); btn_open.setObjectName("ghost")
        btn_open.clicked.connect(self._open_rules_folder)
        path_row.addWidget(self.rules_path_label); path_row.addStretch(); path_row.addWidget(btn_open)
        root.addLayout(path_row)
        self._reload_rules()

    def _reload_rules(self):
        self.rules_list.clear()
        for r in self.user_rules.rules:
            sens = "garder" if r.action == "keep" else "masquer"
            label = f"[{sens}] {r.pattern}  ({r.mode})" + (f" — {r.note}" if r.note else "")
            host = QWidget(); h = QHBoxLayout(host); h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(QLabel(label)); h.addStretch()
            x = QPushButton("✕"); x.setObjectName("ghost"); x.setFixedWidth(30)
            x.clicked.connect(lambda _=False, rule=r: self.remove_rule(rule))
            h.addWidget(x)
            it = QListWidgetItem(); it.setSizeHint(host.sizeHint())
            self.rules_list.addItem(it); self.rules_list.setItemWidget(it, host)

    def _on_add_rule_clicked(self):
        mode = "simple" if self.rule_mode.currentText() == "simple" else "regex"
        action = "keep" if self.rule_action.currentIndex() == 0 else "mask"
        self.add_rule(mode=mode, pattern=self.rule_pattern.text().strip(),
                      action=action, note=self.rule_note.text().strip())

    def add_rule(self, mode: str, pattern: str, action: str, note: str = ""):
        if not pattern:
            self.rule_error.setText("Le motif est vide.")
            return
        if compile_pattern(mode, pattern) is None:
            self.rule_error.setText("Expression régulière invalide.")
            return
        self.rule_error.setText("")
        self.user_rules.rules.append(Rule(mode, pattern, action, True, note))
        self.user_rules = UserRules(self.user_rules.rules)   # recompile
        if self.rules_path:
            self.user_rules.save(self.rules_path)
        self.rule_pattern.clear(); self.rule_note.clear()
        self._reload_rules(); self.on_apply()

    def remove_rule(self, rule: Rule):
        if rule in self.user_rules.rules:
            self.user_rules.rules.remove(rule)
            self.user_rules = UserRules(self.user_rules.rules)
            if self.rules_path:
                self.user_rules.save(self.rules_path)
            self._reload_rules(); self.on_apply()

    def _open_rules_folder(self):
        if not self.rules_path:
            return
        folder = str(Path(self.rules_path).parent)
        if sys.platform.startswith("win"):
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_rules_screen.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/rules_screen.py tests/test_rules_screen.py
git commit -m "feat(ui): écran dédié Gestion des règles (RulesScreen)"
```

---

## Task 2: Écran « À propos » (`AboutScreen`)

**Files:**
- Create: `anonymator/ui/about_screen.py`
- Test: `tests/test_about_screen.py`

- [ ] **Step 1: Écrire le test qui échoue**

Fichier `tests/test_about_screen.py` :

```python
import anonymator
from anonymator.ui.about_screen import AboutScreen


def test_about_screen_shows_legal_lines(qtbot):
    s = AboutScreen(on_back=lambda: None)
    qtbot.addWidget(s)
    text = s.about_label.text()
    assert "AGPL-3.0" in text
    assert f"Anonymator v{anonymator.__version__}" in text
    assert "github.com/gudr-perso/Anonymator" in text


def test_about_screen_back_button_calls_on_back(qtbot):
    called = []
    s = AboutScreen(on_back=lambda: called.append(True))
    qtbot.addWidget(s)
    s.back_btn.click()
    assert called
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_about_screen.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.ui.about_screen'`.

- [ ] **Step 3: Créer `AboutScreen`**

Fichier `anonymator/ui/about_screen.py` :

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.about import about_lines


class AboutScreen(QWidget):
    def __init__(self, on_back):
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(HeaderBand())
        nav = QHBoxLayout()
        self.back_btn = QPushButton("Accueil"); self.back_btn.setObjectName("ghost")
        self.back_btn.clicked.connect(on_back)
        nav.addWidget(self.back_btn); nav.addWidget(QLabel("À propos")); nav.addStretch()
        root.addLayout(nav)

        self.about_label = QLabel("\n".join(about_lines()))
        self.about_label.setObjectName("muted")
        self.about_label.setWordWrap(True)
        root.addWidget(self.about_label)
        root.addStretch()
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_about_screen.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/about_screen.py tests/test_about_screen.py
git commit -m "feat(ui): écran dédié À propos (AboutScreen)"
```

---

## Task 3: Alléger `SettingsScreen`

**Files:**
- Modify: `anonymator/ui/settings_screen.py`
- Modify: `tests/test_settings_screen.py`
- Modify: `tests/test_ui_smoke.py`

Retire le bloc règles + le bloc à propos + le paramètre `rules_path`. Garde thème,
dossier de sortie, types d'entités, section modèle GLiNER.

- [ ] **Step 1: Mettre à jour les tests (retrait règles + à propos)**

Dans `tests/test_settings_screen.py` :

1. Supprimer entièrement la fonction `test_add_and_remove_rule` (lignes 31-47 ;
   déplacée en Task 1).
2. Supprimer entièrement la fonction `test_settings_shows_about_section` (lignes 89-95 ;
   déplacée en Task 2).
3. Les imports top-level (`patch`, `Referential`, `Preferences`, `SettingsScreen`) restent
   valides ; `UserRules` n'était importé que dans le corps de `test_add_and_remove_rule`,
   donc rien à retirer en tête.

Dans `tests/test_ui_smoke.py` :

4. Supprimer entièrement la fonction `test_settings_screen_adds_and_persists_rule`
   (lignes 96-112) : elle éditait les règles via `SettingsScreen(..., rules_path=...)`.
   Sa couverture (persistance disque + `rules_path_label`) est reprise par
   `test_rule_persisted_to_disk` de la Task 1.
   Les autres tests de `test_ui_smoke.py` (MainWindow, HomeScreen positionnel, migration
   stoplist) restent inchangés — ils fonctionneront après les Tasks 4-5.

Les fonctions conservées de `test_settings_screen.py`
(`test_changing_theme_updates_prefs_and_calls_apply`,
`test_toggle_entity_type_updates_overrides`, `_settings`, `test_model_status_absent`,
`test_model_status_present`, `test_model_progress_updates_bar`,
`test_model_finished_emits_ready`) restent inchangées — `_settings()` appelle déjà
`SettingsScreen(...)` sans `rules_path`.

- [ ] **Step 2: Lancer les tests règles/à propos pour vérifier l'échec**

Run: `python -m pytest tests/test_settings_screen.py tests/test_ui_smoke.py -v`
Expected: PASS pour les tests restants (plus aucune référence règles/à propos dans
`test_settings_screen.py` ; `test_ui_smoke.py` ne teste plus l'édition de règles).
Note : à ce stade `SettingsScreen` accepte encore `rules_path` — on le retire en Step 3.

- [ ] **Step 3: Alléger `SettingsScreen`**

Dans `anonymator/ui/settings_screen.py` :

1. **Imports** — retirer `from anonymator.ui.about import about_lines` et
   `from anonymator.user_rules import UserRules, Rule, compile_pattern`.
   Dans l'import `QtWidgets`, retirer `QListWidget, QListWidgetItem` (plus utilisés).
   Retirer aussi les imports `os`, `subprocess`, `sys`, `QLineEdit` **seulement s'ils
   ne sont plus référencés** — `QLineEdit` reste utilisé (dossier de sortie `dir_edit`),
   `os`/`subprocess`/`sys` ne servaient qu'à `_open_rules_folder` → les retirer.
   Garder `from pathlib import Path` (annotation) et `QFileDialog`.

2. **Signature** — remplacer :
   ```python
   def __init__(self, ref, prefs, on_apply, on_back, rules_path: Path | None = None):
       super().__init__()
       self.ref, self.prefs, self.on_apply = ref, prefs, on_apply
       self.rules_path = rules_path
       self.user_rules = UserRules.load(rules_path) if rules_path else UserRules([])
   ```
   par :
   ```python
   def __init__(self, ref, prefs, on_apply, on_back):
       super().__init__()
       self.ref, self.prefs, self.on_apply = ref, prefs, on_apply
   ```

3. **Bloc règles métier** — supprimer tout le bloc entre `root.addWidget(QLabel("Règles métier"))`
   et `self._reload_rules()` inclus (le libellé, `help_rules`, `add_rule_row` et ses widgets,
   `rule_error`, `rules_list`, `path_row`, `rules_path_label`, `btn_open`, l'appel `self._reload_rules()`).

4. **Bloc à propos** — supprimer les 5 lignes finales du `__init__` :
   ```python
   root.addWidget(QLabel("À propos"))
   self.about_label = QLabel("\n".join(about_lines()))
   self.about_label.setObjectName("muted")
   self.about_label.setWordWrap(True)
   root.addWidget(self.about_label)
   ```

5. **Méthodes** — supprimer `_reload_rules`, `_on_add_rule_clicked`, `add_rule`,
   `remove_rule`, `_open_rules_folder`. Garder tout le reste (thème, types, modèle,
   téléchargement, `stop_download`, `closeEvent`, `select_theme`, `set_type_active`, `_choose_dir`).

- [ ] **Step 4: Lancer les tests pour vérifier le succès**

Run: `python -m pytest tests/test_settings_screen.py -v`
Expected: PASS (les tests thème/types/modèle passent ; plus aucune référence règles/à propos).

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/settings_screen.py tests/test_settings_screen.py tests/test_ui_smoke.py
git commit -m "refactor(ui): SettingsScreen n'héberge plus règles ni à propos"
```

---

## Task 4: Deux cartes sur l'accueil (`HomeScreen`)

**Files:**
- Modify: `anonymator/ui/home_screen.py`
- Modify: `tests/test_home_screen.py` (fichier existant — on **ajoute** deux tests)

Contrainte : `on_rules`/`on_about` doivent être **optionnels par mot-clé** (comme
`on_pdf`) pour ne pas casser les appels positionnels existants
(`test_home_screen.py:6,40`, `test_ui_smoke.py:62`, `test_main_window_pdf.py:29` qui
font `HomeScreen(lambda, lambda, lambda, ...)`).

- [ ] **Step 1: Ajouter les tests qui échouent (append au fichier existant)**

À la fin de `tests/test_home_screen.py` (ne rien supprimer de l'existant), ajouter :

```python
def test_rules_card_triggers_callback(qtbot):
    clicked = []
    h = HomeScreen(lambda: None, lambda: None, lambda: None,
                   on_rules=lambda: clicked.append(True))
    qtbot.addWidget(h)
    h.btn_rules.click()
    assert clicked


def test_about_card_triggers_callback(qtbot):
    clicked = []
    h = HomeScreen(lambda: None, lambda: None, lambda: None,
                   on_about=lambda: clicked.append(True))
    qtbot.addWidget(h)
    h.btn_about.click()
    assert clicked
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run: `python -m pytest tests/test_home_screen.py -v`
Expected: les 2 nouveaux tests FAIL — `TypeError` (`__init__` n'accepte pas
`on_rules`/`on_about`). Les tests existants passent encore.

- [ ] **Step 3: Ajouter les cartes à `HomeScreen`**

Dans `anonymator/ui/home_screen.py`, modifier la signature (ajouter `on_rules`,
`on_about` en **kwargs optionnels**, après `on_pdf`) :

```python
    def __init__(self, on_text, on_file, on_settings,
                 model_available: bool = True, on_download=None, on_dismiss=None,
                 on_pdf=None, on_rules=None, on_about=None):
```

Puis remplacer le bloc de création des cartes (`self.btn_settings = NavCard(...)`
et la boucle `for c in (...)`) par :

```python
        self.btn_settings = NavCard("settings", "Paramètres",
                                    "Thème, dossier, types, modèle", on_click=on_settings)
        self.btn_rules = NavCard("shield", "Gestion des règles",
                                 "Règles métier", on_click=on_rules)
        self.btn_about = NavCard("sparkle", "À propos",
                                 "Licence, version et mentions", on_click=on_about)
        for c in (self.btn_text, self.btn_file, self.btn_pdf,
                  self.btn_settings, self.btn_rules, self.btn_about):
            rv.addWidget(c)
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run: `python -m pytest tests/test_home_screen.py -v`
Expected: PASS (tous, dont les 2 nouveaux).

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/home_screen.py tests/test_home_screen.py
git commit -m "feat(ui): accueil — cartes Gestion des règles et À propos"
```

---

## Task 5: Câbler les écrans dans `MainWindow`

**Files:**
- Modify: `anonymator/ui/main_window.py`

- [ ] **Step 1: Ajouter les imports**

Dans `anonymator/ui/main_window.py`, après `from anonymator.ui.settings_screen import SettingsScreen` :

```python
from anonymator.ui.rules_screen import RulesScreen
from anonymator.ui.about_screen import AboutScreen
```

- [ ] **Step 2: Instancier et câbler les écrans**

Remplacer l'instanciation de `self.home` par (ajout de `on_rules`/`on_about`) :

```python
        self.home = HomeScreen(self.show_text, self.show_file, self.show_settings,
                               model_available=is_model_available(),
                               on_download=self._request_model,
                               on_pdf=self.show_pdf,
                               on_rules=self.show_rules, on_about=self.show_about)
```

Remplacer l'instanciation de `self.settings_screen` (retrait de `rules_path`) et
ajouter les deux nouveaux écrans juste après :

```python
        self.settings_screen = SettingsScreen(self.ref, self.prefs,
                                              self._apply_prefs, self.show_home)
        self.rules_screen = RulesScreen(self.rules_path, self._apply_prefs, self.show_home)
        self.about_screen = AboutScreen(self.show_home)
```

Ajouter les deux écrans au `QStackedWidget` — remplacer la boucle `for w in (...)` :

```python
        for w in (self.home, self.text_screen, self.file_screen,
                  self.pdf_screen, self.settings_screen,
                  self.rules_screen, self.about_screen):
            self.stack.addWidget(w)
```

Ajouter les deux navigateurs à la fin de la classe (après `show_settings`) :

```python
    def show_rules(self):
        self.stack.setCurrentWidget(self.rules_screen)

    def show_about(self):
        self.stack.setCurrentWidget(self.about_screen)
```

- [ ] **Step 3: Lancer toute la suite de tests**

Run: `python -m pytest -q`
Expected: PASS sur l'ensemble (aucune régression ; les tests déplacés couvrent règles/à propos).

- [ ] **Step 4: Vérification manuelle rapide (lancement app)**

Run: `python -m anonymator`
Vérifier : l'accueil affiche 6 cartes (Coller / Importer fichier / Importer PDF /
Paramètres / Gestion des règles / À propos) ; chaque nouvelle carte ouvre son écran ;
« Accueil » y ramène ; ajouter une règle dans « Gestion des règles » puis vérifier
qu'elle s'applique dans « Coller du texte ».

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/main_window.py
git commit -m "feat(ui): câble RulesScreen et AboutScreen dans MainWindow"
```

---

## Notes de vérification

- **Point d'entrée app** : confirmer la commande de lancement (`python -m anonymator`
  suppose un `anonymator/__main__.py`). Si absent, utiliser le script de lancement du
  projet (voir `README.md`) — ne pas inventer une commande.
- **`_request_model`** inchangé : il ouvre toujours `SettingsScreen` (le modèle GLiNER
  y reste hébergé), donc l'invite de téléchargement sur l'accueil continue de fonctionner.
- **Migration stoplist→`user_rules.json`** : portée par `MainWindow._build_ref`, non
  touchée ; `RulesScreen` charge le même `rules_path`.
