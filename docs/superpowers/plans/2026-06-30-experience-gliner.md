# Expérience GLiNER « zéro friction » — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre GLiNER non bloquant : l'app démarre toujours sur l'accueil, fonctionne en mode dégradé (règles déterministes) sans le modèle, propose le téléchargement via une carte d'accueil et une section Paramètres avec barre de progression réelle, et reprend la détection complète sans redémarrage une fois le modèle installé.

**Architecture:** La logique de téléchargement vit hors de Qt (`anonymator/core/model_download.py`, testable en patchant `huggingface_hub`). Un `NullNer` (cœur) pilote le mode dégradé. Les écrans Texte/Fichier choisissent leur détecteur à l'analyse (`loader.has_detector() or is_model_available()`). Le `DownloadWorker` (QThread mince) relaie la progression à la section « Modèle de détection » des Paramètres ; `MainWindow` orchestre l'entrée non bloquante et rafraîchit l'UI quand le modèle est prêt. L'écran de setup bloquant est supprimé.

**Tech Stack:** PySide6, pytest-qt (offscreen), huggingface_hub (léger, sans torch), tqdm.

**Référence spec :** [2026-06-30-experience-gliner-design.md](../specs/2026-06-30-experience-gliner-design.md).

**Prérequis :** suite verte (`py -m pytest -q` → 169 passed, 1 deselected). Sur cette machine, l'interpréteur est `py` (Python 3.13) ; `python`/`python3` sont des stubs Windows Store. Le modèle n'est PAS encore en cache (état utilisateur neuf), parfait pour la validation finale.

---

## Structure des fichiers

```
anonymator/ner.py                      MODIFIER : + NullNer
anonymator/core/model_status.py        MODIFIER : + installed_size()
anonymator/core/model_download.py      CRÉER : ProgressTracker, repo_total_size, make_tqdm_class, download_model (non-Qt)
anonymator/ui/model_loader.py          MODIFIER : + has_detector()
anonymator/ui/download_worker.py       RÉÉCRIRE : signaux progress/status/finished/error
anonymator/ui/components/banner.py     CRÉER : ModelBanner (réutilisable texte+fichier)
anonymator/ui/settings_screen.py       MODIFIER : section « Modèle de détection » + signal model_ready
anonymator/ui/home_screen.py           MODIFIER : carte d'invite si modèle absent
anonymator/ui/text_screen.py           MODIFIER : mode dégradé (NullNer + bannière)
anonymator/ui/file_screen.py           MODIFIER : mode dégradé (NullNer + bannière)
anonymator/ui/main_window.py           MODIFIER : entrée non bloquante, orchestration, refresh
anonymator/ui/setup_screen.py          SUPPRIMER
tests/test_ner.py                      CRÉER : NullNer
tests/test_model_status.py             MODIFIER : installed_size
tests/test_model_download.py           CRÉER : ProgressTracker + download_model (patché)
tests/test_model_loader.py             CRÉER : has_detector
tests/test_download_worker.py          CRÉER : relais des signaux (download_model patché)
tests/test_components.py               MODIFIER : ModelBanner
tests/test_settings_screen.py          MODIFIER : section modèle
tests/test_home_screen.py              CRÉER : carte d'invite
tests/test_text_screen.py              MODIFIER : mode dégradé
tests/test_file_screen.py              MODIFIER : mode dégradé
tests/test_ui_smoke.py                 MODIFIER : entrée non bloquante (retrait skip_setup/setup)
tests/test_entrypoint.py               MODIFIER : retrait patch setup
tests/test_setup_screen.py             SUPPRIMER
```

---

### Task 1 : `NullNer` (détecteur vide pour le mode dégradé)

**Files:**
- Modify: `anonymator/ner.py`
- Test: `tests/test_ner.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_ner.py
from anonymator.ner import NullNer


def test_nullner_returns_empty():
    assert NullNer().detect("Jean habite à Toulouse", ["personne", "adresse postale"]) == []


def test_nullner_satisfies_protocol():
    from anonymator.ner import NerDetector
    det: NerDetector = NullNer()
    assert det.detect("x", []) == []
```

- [ ] **Step 2 : Run → FAIL**

Run : `py -m pytest tests/test_ner.py -q`
Expected : FAIL (`ImportError: cannot import name 'NullNer'`).

- [ ] **Step 3 : Implémenter** — ajouter `NullNer` dans `anonymator/ner.py` après la classe `FakeNer`

```python
class NullNer:
    """Détecteur NER vide : aucune détection floue. Sert le mode dégradé
    (modèle GLiNER absent) — les règles déterministes restent actives."""
    def detect(self, text: str, labels: list[str]) -> list[Entity]:
        return []
```

- [ ] **Step 4 : Run → PASS**

Run : `py -m pytest tests/test_ner.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ner.py tests/test_ner.py
git commit -m "feat(ner): NullNer pour le mode dégradé"
```

---

### Task 2 : `installed_size()` (taille du modèle sur disque)

**Files:**
- Modify: `anonymator/core/model_status.py`
- Test: `tests/test_model_status.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_model_status.py  (ajouter)
def test_installed_size_none_when_absent(tmp_path):
    from anonymator.core.model_status import installed_size
    with patch("anonymator.core.model_status.model_cache_dir",
               return_value=tmp_path / "absent"):
        assert installed_size() is None


def test_installed_size_sums_blobs(tmp_path):
    from anonymator.core.model_status import installed_size
    cache = tmp_path / "models--urchade--gliner_multi-v2.1"
    (cache / "snapshots" / "abc").mkdir(parents=True)
    blobs = cache / "blobs"; blobs.mkdir()
    (blobs / "a").write_bytes(b"x" * 100)
    (blobs / "b").write_bytes(b"y" * 50)
    with patch("anonymator.core.model_status.model_cache_dir", return_value=cache):
        assert installed_size() == 150
```

- [ ] **Step 2 : Run → FAIL**

Run : `py -m pytest tests/test_model_status.py -q` → FAIL (`ImportError: installed_size`).

- [ ] **Step 3 : Implémenter** — ajouter à `anonymator/core/model_status.py`

```python
def installed_size() -> int | None:
    """Taille en octets du modèle en cache, ou None s'il n'est pas installé."""
    if not is_model_available():
        return None
    d = model_cache_dir()
    blobs = d / "blobs"
    base = blobs if blobs.exists() else d
    return sum(p.stat().st_size for p in base.rglob("*") if p.is_file())
```

- [ ] **Step 4 : Run → PASS**

Run : `py -m pytest tests/test_model_status.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/core/model_status.py tests/test_model_status.py
git commit -m "feat(model_status): installed_size() pour afficher la taille du modèle"
```

---

### Task 3 : Téléchargement avec progression (cœur, non-Qt)

**Files:**
- Create: `anonymator/core/model_download.py`
- Test: `tests/test_model_download.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_model_download.py
from anonymator.core import model_download


def test_progress_tracker_accumulates():
    seen = []
    t = model_download.ProgressTracker(total=300, emit=lambda r, tot: seen.append((r, tot)))
    t.add(100)
    t.add(50)
    assert seen == [(100, 300), (150, 300)]


def test_download_model_aggregates_progress_across_files(monkeypatch):
    # snapshot_download factice : instancie le tqdm_class et simule deux fichiers
    def fake_snapshot(model_name, tqdm_class=None, **kwargs):
        bar1 = tqdm_class(total=100, unit="B"); bar1.update(100); bar1.close()
        bar2 = tqdm_class(total=200, unit="B"); bar2.update(200); bar2.close()

    monkeypatch.setattr(model_download, "snapshot_download", fake_snapshot)
    monkeypatch.setattr(model_download, "repo_total_size", lambda model_name=None: 300)

    received = []
    statuses = []
    model_download.download_model(on_progress=lambda r, t: received.append((r, t)),
                                  on_status=statuses.append)

    assert received[-1] == (300, 300)         # cumul final sur tous les fichiers
    assert "Téléchargement…" in statuses
```

- [ ] **Step 2 : Run → FAIL**

Run : `py -m pytest tests/test_model_download.py -q` → FAIL (module absent).

- [ ] **Step 3 : Implémenter** `anonymator/core/model_download.py`

```python
from huggingface_hub import HfApi, snapshot_download
from tqdm import tqdm as _base_tqdm
from anonymator.core.model_status import MODEL_NAME


class ProgressTracker:
    """Cumule les octets reçus à travers plusieurs fichiers et émet (reçu, total)."""
    def __init__(self, total, emit):
        self._total = total
        self._received = 0
        self._emit = emit

    def add(self, n: int) -> None:
        self._received += int(n)
        self._emit(self._received, self._total)


def repo_total_size(model_name: str = MODEL_NAME) -> int | None:
    """Somme des tailles des fichiers du dépôt, ou None si indéterminable."""
    try:
        info = HfApi().model_info(model_name, files_metadata=True)
        sizes = [s.size for s in info.siblings if getattr(s, "size", None)]
        return sum(sizes) if sizes else None
    except Exception:        # noqa: BLE001 — total inconnu → barre indéterminée
        return None


def make_tqdm_class(tracker: ProgressTracker):
    """Sous-classe tqdm qui pousse chaque incrément d'octets dans le tracker."""
    class _Tqdm(_base_tqdm):
        def update(self, n=1):
            tracker.add(n or 0)
            return super().update(n)
    return _Tqdm


def download_model(on_progress=None, on_status=None) -> None:
    """Télécharge le modèle GLiNER dans le cache HuggingFace, en signalant
    la progression. `on_progress(reçu, total)` (total peut être None),
    `on_status(texte)`."""
    if on_status:
        on_status("Connexion…")
    total = repo_total_size()
    tqdm_class = None
    if on_progress is not None:
        tracker = ProgressTracker(total, on_progress)
        tqdm_class = make_tqdm_class(tracker)
    if on_status:
        on_status("Téléchargement…")
    snapshot_download(MODEL_NAME, tqdm_class=tqdm_class)
    if on_status:
        on_status("Finalisation…")
```

- [ ] **Step 4 : Run → PASS**

Run : `py -m pytest tests/test_model_download.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/core/model_download.py tests/test_model_download.py
git commit -m "feat(core): téléchargement modèle avec progression agrégée (non-Qt)"
```

---

### Task 4 : `ModelLoader.has_detector()`

**Files:**
- Modify: `anonymator/ui/model_loader.py`
- Test: `tests/test_model_loader.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_model_loader.py
from anonymator.ui.model_loader import ModelLoader
from anonymator.ner import FakeNer


def test_has_detector_true_when_injected():
    assert ModelLoader(FakeNer({})).has_detector() is True


def test_has_detector_false_when_lazy():
    assert ModelLoader().has_detector() is False
```

- [ ] **Step 2 : Run → FAIL**

Run : `py -m pytest tests/test_model_loader.py -q` → FAIL (`AttributeError: has_detector`).

- [ ] **Step 3 : Implémenter** — ajouter à `anonymator/ui/model_loader.py`

```python
    def has_detector(self) -> bool:
        """True si un détecteur est déjà disponible (injecté), sans charger GLiNER."""
        return self._detector is not None
```

- [ ] **Step 4 : Run → PASS**

Run : `py -m pytest tests/test_model_loader.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/model_loader.py tests/test_model_loader.py
git commit -m "feat(loader): has_detector() pour décider du mode dégradé"
```

---

### Task 5 : `DownloadWorker` (QThread mince relayant la progression)

**Files:**
- Modify (réécrire): `anonymator/ui/download_worker.py`
- Test: `tests/test_download_worker.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_download_worker.py
from anonymator.ui import download_worker
from anonymator.ui.download_worker import DownloadWorker


def test_worker_emits_progress_and_finished(qtbot, monkeypatch):
    def fake_download(on_progress=None, on_status=None):
        if on_status:
            on_status("Téléchargement…")
        if on_progress:
            on_progress(150, 300)

    monkeypatch.setattr(download_worker, "download_model", fake_download)
    w = DownloadWorker()
    progresses, statuses = [], []
    w.progress.connect(lambda r, t: progresses.append((r, t)))
    w.status.connect(statuses.append)
    with qtbot.waitSignal(w.download_finished, timeout=3000):
        w.start()
    assert (150, 300) in progresses
    assert "Téléchargement…" in statuses


def test_worker_emits_error(qtbot, monkeypatch):
    def boom(on_progress=None, on_status=None):
        raise RuntimeError("pas de réseau")

    monkeypatch.setattr(download_worker, "download_model", boom)
    w = DownloadWorker()
    errors = []
    w.error.connect(errors.append)
    with qtbot.waitSignal(w.error, timeout=3000):
        w.start()
    assert "pas de réseau" in errors[0]
```

- [ ] **Step 2 : Run → FAIL**

Run : `py -m pytest tests/test_download_worker.py -q` → FAIL (signaux/attributs absents).

- [ ] **Step 3 : Implémenter** — remplacer tout le contenu de `anonymator/ui/download_worker.py`

```python
from PySide6.QtCore import QThread, Signal
from anonymator.core.model_download import download_model


class DownloadWorker(QThread):
    progress = Signal(int, int)      # (octets reçus, total ; total=0 si inconnu)
    status = Signal(str)
    download_finished = Signal()
    error = Signal(str)

    def run(self):
        try:
            download_model(
                on_progress=lambda r, t: self.progress.emit(r, t or 0),
                on_status=self.status.emit,
            )
            self.download_finished.emit()
        except Exception as exc:     # noqa: BLE001 — remonté à l'UI
            self.error.emit(str(exc))
```

- [ ] **Step 4 : Run → PASS**

Run : `py -m pytest tests/test_download_worker.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/download_worker.py tests/test_download_worker.py
git commit -m "feat(ui): DownloadWorker relaie progression/erreur du téléchargement"
```

---

### Task 6 : `ModelBanner` (bannière dégradé réutilisable)

**Files:**
- Create: `anonymator/ui/components/banner.py`
- Test: `tests/test_components.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_components.py  (ajouter)
def test_model_banner_install_callback(qtbot):
    from anonymator.ui.components.banner import ModelBanner
    called = []
    b = ModelBanner(on_install=lambda: called.append(True))
    qtbot.addWidget(b)
    b.btn.click()
    assert called == [True]
```

- [ ] **Step 2 : Run → FAIL**

Run : `py -m pytest tests/test_components.py::test_model_banner_install_callback -q` → FAIL (module absent).

- [ ] **Step 3 : Implémenter** `anonymator/ui/components/banner.py`

```python
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton


class ModelBanner(QWidget):
    """Bandeau « mode dégradé » : noms/adresses/orgs non détectés faute de modèle."""
    def __init__(self, on_install=None, parent=None):
        super().__init__(parent)
        self.setObjectName("modelBanner")
        h = QHBoxLayout(self); h.setContentsMargins(12, 8, 12, 8); h.setSpacing(10)
        lbl = QLabel("⚠  Noms / adresses / organisations non détectés "
                     "(modèle non installé).")
        lbl.setWordWrap(True)
        self.btn = QPushButton("Installer maintenant"); self.btn.setObjectName("secondary")
        if on_install is not None:
            self.btn.clicked.connect(on_install)
        h.addWidget(lbl); h.addStretch(); h.addWidget(self.btn)
        self.setStyleSheet(
            "#modelBanner { background: rgba(232, 98, 26, 0.10); "
            "border: 1px solid rgba(232, 98, 26, 0.55); border-radius: 8px; }")
        self.hide()
```

- [ ] **Step 4 : Run → PASS**

Run : `py -m pytest tests/test_components.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/components/banner.py tests/test_components.py
git commit -m "feat(ui): composant ModelBanner (mode dégradé)"
```

---

### Task 7 : Paramètres — section « Modèle de détection »

**Files:**
- Modify: `anonymator/ui/settings_screen.py`
- Test: `tests/test_settings_screen.py`

La section affiche le statut (installé + taille / non installé), un bouton Télécharger/Réparer, une barre de progression et un texte explicatif ; elle expose un signal `model_ready` et une méthode publique `start_model_download()` (appelée aussi depuis l'accueil et les bannières via `MainWindow`).

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_settings_screen.py  (ajouter en tête)
from unittest.mock import patch

def _settings(prefs=None):
    from anonymator.referential import Referential
    from anonymator.ui.preferences import Preferences
    from anonymator.ui.settings_screen import SettingsScreen
    return SettingsScreen(Referential.load_default(), prefs or Preferences(),
                          on_apply=lambda: None, on_back=lambda: None)

def test_model_status_absent(qtbot):
    with patch("anonymator.ui.settings_screen.is_model_available", return_value=False):
        s = _settings(); qtbot.addWidget(s)
        assert "non installé" in s.model_status_label.text().lower()
        assert s.btn_model.text() == "Télécharger"

def test_model_status_present(qtbot):
    with patch("anonymator.ui.settings_screen.is_model_available", return_value=True), \
         patch("anonymator.ui.settings_screen.installed_size", return_value=300 * 1024 * 1024):
        s = _settings(); qtbot.addWidget(s)
        assert "installé" in s.model_status_label.text().lower()
        assert s.btn_model.text() == "Réparer (re-télécharger)"

def test_model_progress_updates_bar(qtbot):
    with patch("anonymator.ui.settings_screen.is_model_available", return_value=False):
        s = _settings(); qtbot.addWidget(s)
        s._on_model_progress(150 * 1024 * 1024, 300 * 1024 * 1024)
        assert s.model_progress.maximum() == 300 * 1024 * 1024
        assert s.model_progress.value() == 150 * 1024 * 1024

def test_model_finished_emits_ready(qtbot):
    with patch("anonymator.ui.settings_screen.is_model_available", return_value=False):
        s = _settings(); qtbot.addWidget(s)
        ready = []
        s.model_ready.connect(lambda: ready.append(True))
        with patch("anonymator.ui.settings_screen.is_model_available", return_value=True), \
             patch("anonymator.ui.settings_screen.installed_size", return_value=10):
            s._on_model_finished()
        assert ready == [True]
        assert "installé" in s.model_status_label.text().lower()
```

- [ ] **Step 2 : Run → FAIL**

Run : `py -m pytest tests/test_settings_screen.py -q` → FAIL (attributs/méthodes absents).

- [ ] **Step 3 : Implémenter**

Dans `anonymator/ui/settings_screen.py`, étendre les imports en tête :

```python
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QLineEdit, QFileDialog,
                               QListWidget, QListWidgetItem, QScrollArea, QProgressBar)
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.toggle import ToggleSwitch
from anonymator.referential import Referential
from anonymator.core.model_status import is_model_available, installed_size
from anonymator.ui.download_worker import DownloadWorker
```

Déclarer le signal sur la classe (juste sous `class SettingsScreen(QWidget):`) :

```python
    model_ready = Signal()
```

À la fin de `__init__` (après la liste d'exclusion), ajouter la section et initialiser le worker :

```python
        self._dl_worker: DownloadWorker | None = None
        root.addWidget(QLabel("Modèle de détection (noms, adresses, organisations)"))
        explain = QLabel(
            "La détection intelligente des noms, adresses et organisations utilise "
            "le modèle GLiNER (~300 Mo), téléchargé une seule fois puis utilisé hors ligne. "
            "Sans lui, les détections par règles (IBAN, e-mail, téléphone, mots de passe…) "
            "fonctionnent quand même.")
        explain.setWordWrap(True); explain.setObjectName("muted")
        root.addWidget(explain)
        self.model_status_label = QLabel("")
        root.addWidget(self.model_status_label)
        self.model_location_label = QLabel(""); self.model_location_label.setObjectName("muted")
        self.model_location_label.setWordWrap(True)
        root.addWidget(self.model_location_label)
        self.btn_model = QPushButton(""); self.btn_model.setObjectName("primary")
        self.btn_model.clicked.connect(self.start_model_download)
        root.addWidget(self.btn_model)
        self.model_progress = QProgressBar(); self.model_progress.setVisible(False)
        root.addWidget(self.model_progress)
        self.model_dl_status = QLabel(""); self.model_dl_status.setObjectName("muted")
        root.addWidget(self.model_dl_status)
        self._refresh_model_section()
```

Ajouter les méthodes (helpers + handlers) :

```python
    @staticmethod
    def _human_mb(n: int) -> str:
        return f"{n / (1024 * 1024):.0f} Mo"

    def _refresh_model_section(self):
        from anonymator.core.model_status import model_cache_dir
        if is_model_available():
            size = installed_size() or 0
            self.model_status_label.setText(f"✅ Installé ({self._human_mb(size)})")
            self.btn_model.setText("Réparer (re-télécharger)")
        else:
            self.model_status_label.setText("⬜ Non installé")
            self.btn_model.setText("Télécharger")
        self.model_location_label.setText(f"Emplacement : {model_cache_dir()}")

    def start_model_download(self):
        if self._dl_worker is not None and self._dl_worker.isRunning():
            return
        self.btn_model.setEnabled(False)
        self.model_progress.setVisible(True)
        self.model_progress.setRange(0, 0)          # indéterminé tant qu'on n'a pas le total
        self.model_dl_status.setText("Démarrage…")
        self._dl_worker = DownloadWorker()
        self._dl_worker.progress.connect(self._on_model_progress)
        self._dl_worker.status.connect(self.model_dl_status.setText)
        self._dl_worker.download_finished.connect(self._on_model_finished)
        self._dl_worker.error.connect(self._on_model_error)
        self._dl_worker.finished.connect(self._dl_worker.deleteLater)
        self._dl_worker.start()

    def _on_model_progress(self, received: int, total: int):
        if total > 0:
            self.model_progress.setRange(0, total)
            self.model_progress.setValue(received)
            self.model_dl_status.setText(
                f"{self._human_mb(received)} / {self._human_mb(total)} "
                f"— {received * 100 // total} %")
        else:
            self.model_progress.setRange(0, 0)

    def _on_model_finished(self):
        self.model_progress.setVisible(False)
        self.btn_model.setEnabled(True)
        self._refresh_model_section()
        self.model_dl_status.setText("Modèle prêt.")
        self.model_ready.emit()

    def _on_model_error(self, msg: str):
        self.model_progress.setVisible(False)
        self.btn_model.setEnabled(True)
        self.model_dl_status.setText(f"Erreur : {msg}")

    def closeEvent(self, event):
        if self._dl_worker is not None and self._dl_worker.isRunning():
            self._dl_worker.quit(); self._dl_worker.wait()
        super().closeEvent(event)
```

- [ ] **Step 4 : Run → PASS**

Run : `py -m pytest tests/test_settings_screen.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/settings_screen.py tests/test_settings_screen.py
git commit -m "feat(settings): section Modèle de détection (statut, téléchargement, progression)"
```

---

### Task 8 : Accueil — carte d'invite si modèle absent

**Files:**
- Modify: `anonymator/ui/home_screen.py`
- Test: `tests/test_home_screen.py`

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_home_screen.py
from anonymator.ui.home_screen import HomeScreen


def _home(model_available, dl=None, later=None):
    return HomeScreen(lambda: None, lambda: None, lambda: None,
                      model_available=model_available,
                      on_download=dl or (lambda: None),
                      on_dismiss=later or (lambda: None))


def test_invite_visible_when_model_absent(qtbot):
    h = _home(False); qtbot.addWidget(h)
    assert h.model_card.isVisibleTo(h) is True


def test_invite_hidden_when_model_present(qtbot):
    h = _home(True); qtbot.addWidget(h)
    assert h.model_card.isVisibleTo(h) is False


def test_invite_download_and_dismiss(qtbot):
    calls = []
    h = _home(False, dl=lambda: calls.append("dl"), later=lambda: calls.append("later"))
    qtbot.addWidget(h)
    h.btn_model_download.click()
    h.btn_model_later.click()
    assert calls == ["dl", "later"]
    assert h.model_card.isVisibleTo(h) is False   # « Plus tard » masque la carte


def test_set_model_available_hides_card(qtbot):
    h = _home(False); qtbot.addWidget(h)
    h.set_model_available(True)
    assert h.model_card.isVisibleTo(h) is False


def test_navcards_still_callable_with_defaults(qtbot):
    calls = []
    h = HomeScreen(lambda: calls.append("t"), lambda: calls.append("f"),
                   lambda: calls.append("s"))
    qtbot.addWidget(h)
    h.btn_text._emit(); h.btn_file._emit(); h.btn_settings._emit()
    assert calls == ["t", "f", "s"]
```

- [ ] **Step 2 : Run → FAIL**

Run : `py -m pytest tests/test_home_screen.py -q` → FAIL (paramètres/attributs absents).

- [ ] **Step 3 : Implémenter**

Dans `anonymator/ui/home_screen.py`, étendre la signature et construire la carte. Remplacer l'en-tête de `HomeScreen.__init__` :

```python
    def __init__(self, on_text, on_file, on_settings,
                 model_available: bool = True, on_download=None, on_dismiss=None):
        super().__init__()
        self._on_dismiss = on_dismiss
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
```

Ajouter `QPushButton` aux imports Qt en tête du fichier :

```python
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
```

Dans la colonne de droite (`rv`), insérer la carte d'invite **avant** le label « PAR OÙ COMMENCER ? » :

```python
        self.model_card = QWidget(); self.model_card.setObjectName("modelInvite")
        mc = QVBoxLayout(self.model_card); mc.setContentsMargins(16, 14, 16, 14); mc.setSpacing(8)
        mc_title = QLabel("🧠  Activer la détection intelligente")
        mc_title.setStyleSheet("font-weight: 700; font-size: 15px;")
        mc_desc = QLabel("Noms, adresses et organisations — téléchargement unique (~300 Mo). "
                         "Les détections par règles (IBAN, e-mail, téléphone…) fonctionnent déjà sans elle.")
        mc_desc.setWordWrap(True); mc_desc.setObjectName("muted")
        mc_btns = QHBoxLayout()
        self.btn_model_download = QPushButton("Télécharger maintenant")
        self.btn_model_download.setObjectName("primary")
        if on_download is not None:
            self.btn_model_download.clicked.connect(on_download)
        self.btn_model_later = QPushButton("Plus tard"); self.btn_model_later.setObjectName("ghost")
        self.btn_model_later.clicked.connect(self._dismiss)
        mc_btns.addWidget(self.btn_model_download); mc_btns.addWidget(self.btn_model_later); mc_btns.addStretch()
        mc.addWidget(mc_title); mc.addWidget(mc_desc); mc.addLayout(mc_btns)
        self.model_card.setStyleSheet(
            "#modelInvite { background: rgba(0, 150, 94, 0.08); "
            "border: 1px solid rgba(0, 150, 94, 0.45); border-radius: 10px; }")
        self.model_card.setVisible(not model_available)
        rv.addWidget(self.model_card); rv.addSpacing(12)
```

Ajouter les méthodes à la fin de la classe :

```python
    def _dismiss(self):
        self.model_card.setVisible(False)
        if self._on_dismiss is not None:
            self._on_dismiss()

    def set_model_available(self, available: bool):
        self.model_card.setVisible(not available)
```

> Note : `rv` est défini plus bas dans `__init__` actuel. Déplacer le bloc carte **après** la
> création de `right`/`rv` (`rv = QVBoxLayout(right)`) et **avant** `rv.addWidget(label)`.

- [ ] **Step 4 : Run → PASS**

Run : `py -m pytest tests/test_home_screen.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/home_screen.py tests/test_home_screen.py
git commit -m "feat(home): carte d'invite de téléchargement du modèle"
```

---

### Task 9 : Mode dégradé écran Texte (NullNer + bannière)

**Files:**
- Modify: `anonymator/ui/text_screen.py`
- Test: `tests/test_text_screen.py`

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_text_screen.py  (ajouter)
from unittest.mock import patch
from anonymator.ui.text_screen import TextScreen
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.referential import Referential
from anonymator.ner import FakeNer


def test_degraded_banner_when_model_absent(qtbot):
    with patch("anonymator.ui.text_screen.is_model_available", return_value=False):
        s = TextScreen(Referential.load_default(), ModelLoader(), Preferences(),
                       on_back=lambda: None, on_request_model=lambda: None)
        qtbot.addWidget(s)
        s.input.setPlainText("IBAN FR76 3000 6000 0112 3456 7890 189 pour Claire Martin")
        s.analyze()
        qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
        assert s._degraded is True
        assert s.banner.isVisibleTo(s) is True
        # règles déterministes toujours actives : l'IBAN est détecté
        assert any(e.type == "IBAN" for e in s.session.entities())


def test_no_banner_when_detector_injected(qtbot):
    with patch("anonymator.ui.text_screen.is_model_available", return_value=False):
        s = TextScreen(Referential.load_default(),
                       ModelLoader(FakeNer({"Claire Martin": "PERSON"})),
                       Preferences(), on_back=lambda: None)
        qtbot.addWidget(s)
        s.input.setPlainText("Bonjour Claire Martin")
        s.analyze()
        qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
        assert s._degraded is False
        assert s.banner.isVisibleTo(s) is False


def test_banner_install_calls_request_model(qtbot):
    called = []
    with patch("anonymator.ui.text_screen.is_model_available", return_value=False):
        s = TextScreen(Referential.load_default(), ModelLoader(), Preferences(),
                       on_back=lambda: None, on_request_model=lambda: called.append(True))
        qtbot.addWidget(s)
        s.banner.btn.click()
    assert called == [True]
```

- [ ] **Step 2 : Run → FAIL**

Run : `py -m pytest tests/test_text_screen.py -q` → FAIL (paramètre/attributs absents).

- [ ] **Step 3 : Implémenter**

Dans `anonymator/ui/text_screen.py`, étendre les imports en tête :

```python
from anonymator.core.model_status import is_model_available
from anonymator.ner import NullNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.components.banner import ModelBanner
```

Modifier la signature et l'état initial de `__init__` :

```python
    def __init__(self, ref, loader, prefs, on_back, on_request_model=None):
        super().__init__()
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.on_request_model = on_request_model
        self.session: ReviewSession | None = None
        self._worker: TextAnalyzeWorker | None = None
        self._degraded = False
```

Juste après `root.addWidget(HeaderBand())`, insérer la bannière :

```python
        self.banner = ModelBanner(on_install=self._request_model)
        root.addWidget(self.banner)
```

Remplacer la méthode `analyze` :

```python
    def analyze(self):
        if self._worker is not None and self._worker.isRunning():
            return
        text = self.input.toPlainText()
        self._degraded = not (self.loader.has_detector() or is_model_available())
        loader = ModelLoader(NullNer()) if self._degraded else self.loader
        self._set_busy(True)
        self._worker = TextAnalyzeWorker(text, loader, self.ref)
        self._worker.done.connect(self._on_analyzed)
        self._worker.error.connect(self._on_analyze_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()
```

Dans `_on_analyzed`, afficher/masquer la bannière (ajouter une ligne) :

```python
    def _on_analyzed(self, text, ents):
        self.session = ReviewSession(text, ents)
        self.banner.setVisible(self._degraded)
        self._refresh_entities(); self._highlight(); self._refresh_stats()
        self._set_busy(False)
```

Ajouter le relais d'installation et le masquage de bannière à la fin de la classe :

```python
    def _request_model(self):
        if self.on_request_model is not None:
            self.on_request_model()

    def hide_degraded(self):
        self._degraded = False
        self.banner.setVisible(False)
```

- [ ] **Step 4 : Run → PASS**

Run : `py -m pytest tests/test_text_screen.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/text_screen.py tests/test_text_screen.py
git commit -m "feat(text): mode dégradé (NullNer + bannière modèle absent)"
```

---

### Task 10 : Mode dégradé écran Fichier (NullNer + bannière)

**Files:**
- Modify: `anonymator/ui/file_screen.py`
- Test: `tests/test_file_screen.py`

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_file_screen.py  (ajouter)
from unittest.mock import patch

def test_file_degraded_banner_when_model_absent(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;IBAN\nClaire Martin;FR7630006000011234567890189\n".encode("cp1252"))
    with patch("anonymator.ui.file_screen.is_model_available", return_value=False):
        ref = Referential.load_default()
        loader = ModelLoader()
        s = FileScreen(ref, loader, Preferences(), on_back=lambda: None,
                       on_request_model=lambda: None)
        qtbot.addWidget(s)
        s.load_path(str(src))
        s.analyze()
        qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
        assert s._degraded is True
        assert s.banner.isVisibleTo(s) is True

def test_file_no_banner_with_injected_detector(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    with patch("anonymator.ui.file_screen.is_model_available", return_value=False):
        s = FileScreen(Referential.load_default(),
                       ModelLoader(FakeNer({"Claire Martin": "PERSON"})),
                       Preferences(), on_back=lambda: None)
        qtbot.addWidget(s)
        s.load_path(str(src)); s.analyze()
        qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
        assert s._degraded is False
        assert s.banner.isVisibleTo(s) is False
```

> Les imports `ModelLoader`, `FakeNer`, `Preferences`, `Referential` existent déjà en tête de
> `tests/test_file_screen.py` (helpers `_screen`). Réutiliser ; n'ajouter que `from unittest.mock import patch` si absent.

- [ ] **Step 2 : Run → FAIL**

Run : `py -m pytest tests/test_file_screen.py -q` → FAIL (paramètre/attributs absents).

- [ ] **Step 3 : Implémenter**

Dans `anonymator/ui/file_screen.py`, étendre les imports en tête :

```python
from anonymator.core.model_status import is_model_available
from anonymator.ner import NullNer
from anonymator.ui.components.banner import ModelBanner
```

Modifier la signature et l'état initial de `__init__` :

```python
    def __init__(self, ref, loader, prefs, on_back, on_text_review=None, on_request_model=None):
        super().__init__()
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.on_text_review = on_text_review
        self.on_request_model = on_request_model
        self.path: Path | None = None
        self.doc = None
        self.session: FileReviewSession | None = None
        self.page = 0
        self._busy = False
        self._degraded = False
        self._worker: FileScanWorker | None = None
```

Juste après `root.addWidget(HeaderBand())`, insérer la bannière :

```python
        self.banner = ModelBanner(on_install=self._request_model)
        root.addWidget(self.banner)
```

Dans `analyze`, calculer le mode et choisir le détecteur. Remplacer le bloc CSV (à partir de `cols = default_maskable_columns(...)`) :

```python
        cols = default_maskable_columns(self.doc.rows, self.doc.has_header)
        self._cols = cols
        self._degraded = not (self.loader.has_detector() or is_model_available())
        ner = NullNer() if self._degraded else self.loader.get()
        self._set_busy(True)
        self._worker = FileScanWorker(self.doc, ner, self.ref, cols)
        self._worker.scan_finished.connect(self._on_scanned)
        self._worker.error.connect(self._on_scan_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()
```

Dans `_on_scanned`, afficher/masquer la bannière (ajouter une ligne après `self._set_busy(False)`) :

```python
        self.banner.setVisible(self._degraded)
```

Ajouter à la fin de la classe :

```python
    def _request_model(self):
        if self.on_request_model is not None:
            self.on_request_model()

    def hide_degraded(self):
        self._degraded = False
        self.banner.setVisible(False)
```

- [ ] **Step 4 : Run → PASS**

Run : `py -m pytest tests/test_file_screen.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/file_screen.py tests/test_file_screen.py
git commit -m "feat(file): mode dégradé (NullNer + bannière modèle absent)"
```

---

### Task 11 : `MainWindow` non bloquant + orchestration ; suppression du setup

**Files:**
- Modify: `anonymator/ui/main_window.py`
- Delete: `anonymator/ui/setup_screen.py`, `tests/test_setup_screen.py`
- Test: `tests/test_ui_smoke.py`, `tests/test_entrypoint.py`

- [ ] **Step 1 : Mettre à jour les tests (qui échoueront)**

Remplacer **tout** le contenu de `tests/test_ui_smoke.py` par :

```python
# tests/test_ui_smoke.py
from unittest.mock import patch
from anonymator.ui.main_window import MainWindow


def test_main_window_builds_and_has_home(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        win = MainWindow()
    qtbot.addWidget(win)
    assert win.stack.count() >= 1
    assert win.home.btn_text is not None
    assert win.home.btn_file is not None


def test_navigation_to_text_and_file(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        win = MainWindow()
    qtbot.addWidget(win)
    win.show_text(); assert win.stack.currentWidget() is win.text_screen
    win.show_file(); assert win.stack.currentWidget() is win.file_screen
    win.show_home(); assert win.stack.currentWidget() is win.home


def test_starts_on_home_even_when_model_absent(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=False):
        win = MainWindow()
        qtbot.addWidget(win)
        assert win.stack.currentWidget() is win.home          # plus de setup bloquant
        assert win.home.model_card.isVisibleTo(win.home) is True


def test_request_model_navigates_to_settings(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=False):
        win = MainWindow()
        qtbot.addWidget(win)
        with patch.object(win.settings_screen, "start_model_download") as start:
            win._request_model()
            assert win.stack.currentWidget() is win.settings_screen
            start.assert_called_once()


def test_model_ready_hides_invite(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=False):
        win = MainWindow()
        qtbot.addWidget(win)
        win._on_model_ready()
        assert win.home.model_card.isVisibleTo(win.home) is False


def test_home_navcards_trigger_callbacks(qtbot):
    from anonymator.ui.home_screen import HomeScreen
    calls = []
    h = HomeScreen(lambda: calls.append("t"), lambda: calls.append("f"),
                   lambda: calls.append("s"))
    qtbot.addWidget(h)
    h.btn_text._emit(); h.btn_file._emit(); h.btn_settings._emit()
    assert calls == ["t", "f", "s"]


def test_referential_uses_prefs_overrides(qtbot, tmp_path):
    from anonymator.ui.model_loader import ModelLoader
    from anonymator.ner import FakeNer
    prefs_path = tmp_path / "prefs.json"
    prefs_path.write_text('{"theme":"cuma","entity_overrides":{"BIC":true},'
                          '"ner_stoplist":["truc"]}', encoding="utf-8")
    win = MainWindow(loader=ModelLoader(FakeNer({})), prefs_path=prefs_path)
    qtbot.addWidget(win)
    assert win.ref.is_active("BIC") is True
    assert "truc" in win.ref.ner_stoplist()
```

Supprimer le fichier `tests/test_setup_screen.py` :

```bash
git rm tests/test_setup_screen.py
```

- [ ] **Step 2 : Run → FAIL**

Run : `py -m pytest tests/test_ui_smoke.py -q` → FAIL (`skip_setup`/`setup_screen` disparus, `_request_model` absent).

- [ ] **Step 3 : Implémenter** — réécrire `anonymator/ui/main_window.py`

```python
# anonymator/ui/main_window.py
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QStackedWidget
from anonymator.referential import Referential
from anonymator.ui.preferences import Preferences
from anonymator.ui.theme import build_qss
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.home_screen import HomeScreen
from anonymator.ui.text_screen import TextScreen
from anonymator.ui.file_screen import FileScreen
from anonymator.ui.settings_screen import SettingsScreen
from anonymator.core.model_status import is_model_available

_ASSETS = Path(__file__).parent / "assets"

PREFS_PATH = Path.home() / ".anonymator" / "preferences.json"


class MainWindow(QMainWindow):
    def __init__(self, loader: ModelLoader | None = None,
                 prefs_path: Path = PREFS_PATH):
        super().__init__()
        self.setWindowTitle("Anonymator")
        ico = _ASSETS / "anonymator.ico"
        if ico.exists():
            self.setWindowIcon(QIcon(str(ico)))
        self.prefs_path = prefs_path
        self.prefs = Preferences.load(prefs_path)
        self.ref = self._build_ref()
        self.loader = loader or ModelLoader()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.home = HomeScreen(self.show_text, self.show_file, self.show_settings,
                               model_available=is_model_available(),
                               on_download=self._request_model)
        self.text_screen = TextScreen(self.ref, self.loader, self.prefs,
                                      self.show_home, on_request_model=self._request_model)
        self.file_screen = FileScreen(self.ref, self.loader, self.prefs,
                                      self.show_home, on_text_review=self._review_text,
                                      on_request_model=self._request_model)
        self.settings_screen = SettingsScreen(self.ref, self.prefs,
                                              self._apply_prefs, self.show_home)
        for w in (self.home, self.text_screen, self.file_screen, self.settings_screen):
            self.stack.addWidget(w)

        self.settings_screen.model_ready.connect(self._on_model_ready)

        self.show_home()          # toujours non bloquant
        self._apply_theme()

    def _build_ref(self):
        ref = Referential.load_default(overrides=self.prefs.entity_overrides)
        if self.prefs.ner_stoplist is not None:
            ref = ref.with_stoplist(self.prefs.ner_stoplist)
        return ref

    def _apply_theme(self):
        self.setStyleSheet(build_qss(self.prefs.theme))

    def _apply_prefs(self):
        self.prefs.save(self.prefs_path)
        self.ref = self._build_ref()
        self.text_screen.ref = self.ref
        self.file_screen.ref = self.ref
        self._apply_theme()

    def _request_model(self):
        """Depuis la carte d'accueil ou une bannière dégradé : aller aux Paramètres
        et lancer le téléchargement."""
        self.show_settings()
        self.settings_screen.start_model_download()

    def _on_model_ready(self):
        self.home.set_model_available(True)
        self.text_screen.hide_degraded()
        self.file_screen.hide_degraded()

    def _review_text(self, text: str):
        self.text_screen.input.setPlainText(text)
        self.stack.setCurrentWidget(self.text_screen)
        self.text_screen.analyze()

    def show_home(self):
        self.stack.setCurrentWidget(self.home)

    def show_text(self):
        self.stack.setCurrentWidget(self.text_screen)

    def show_file(self):
        self.stack.setCurrentWidget(self.file_screen)

    def show_settings(self):
        self.stack.setCurrentWidget(self.settings_screen)
```

Supprimer le fichier de l'écran de setup :

```bash
git rm anonymator/ui/setup_screen.py
```

- [ ] **Step 4 : Run → PASS**

Run : `py -m pytest tests/test_ui_smoke.py tests/test_entrypoint.py -q` → PASS.
Puis suite complète : `py -m pytest -q` → verte (aucune référence résiduelle à `setup_screen`/`skip_setup`).

> `tests/test_entrypoint.py` patche déjà `anonymator.ui.main_window.is_model_available` et
> n'utilise pas `skip_setup` → il reste valide tel quel. Si une référence à `skip_setup` y subsiste,
> la retirer.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/main_window.py tests/test_ui_smoke.py tests/test_entrypoint.py
git commit -m "feat(ui): démarrage non bloquant + orchestration modèle ; suppression setup bloquant"
```

---

### Task 12 : Build exe + validation manuelle « à l'identique de l'utilisateur »

**Files:** aucun (validation). Cette machine est vierge de modèle → état utilisateur neuf.

- [ ] **Step 1 : Suite verte**

Run : `py -m pytest -q`
Expected : tout vert (1 deselected).

- [ ] **Step 2 : Rebuild de l'exe**

Run : `py -m PyInstaller anonymator.spec -y`
Expected : `Build complete!` ; `dist/anonymator/anonymator.exe` régénéré.

- [ ] **Step 3 : Validation manuelle via l'exe uniquement**

Lancer `dist/anonymator/anonymator.exe` et vérifier, dans l'ordre :
1. L'app ouvre **directement sur l'accueil** (pas d'écran bloquant) ; la **carte d'invite** est visible.
2. Aller dans **Texte**, coller « IBAN FR76 3000 6000 0112 3456 7890 189 pour Claire Martin »,
   cliquer **Analyser** : l'IBAN est détecté/masquable, « Claire Martin » **non** détecté, la
   **bannière dégradé** s'affiche.
3. Cliquer **Installer maintenant** (ou aller dans **Paramètres** → section « Modèle de détection »
   → **Télécharger**) : la **barre de progression réelle** progresse (% + Mo) jusqu'à 100 %.
4. Le statut Paramètres passe à **« ✅ Installé (… Mo) »** ; revenir à **Texte**, **Analyser** de
   nouveau : « Claire Martin » est maintenant détecté, **plus de bannière** ; revenir à l'accueil :
   la carte d'invite a **disparu**.

- [ ] **Step 4 : Commit (si l'exe/le spec ont changé)**

```bash
git add -A
git commit -m "chore: rebuild exe après expérience GLiNER zéro friction"
```

---

## Auto-revue (plan vs spec)

- §3.1 Premier lancement non bloquant + carte d'invite → Tasks 8, 11. ✓
- §3.2 / §4.2 Mode dégradé (NullNer + bannière, déterministe actif) → Tasks 1, 9, 10. ✓
- §3.3 Décision détecteur (`has_detector or is_model_available`) → Tasks 4, 9, 10. ✓
- §4.3 Téléchargement + barre % réelle + statut + erreurs → Tasks 3, 5, 7. ✓
- §5.1 `NullNer`, `installed_size` → Tasks 1, 2. ✓
- §5.2 Worker progression → Tasks 3, 5. ✓
- §5.3 Section Paramètres, carte accueil, bannières écrans, orchestration MainWindow, suppression
  setup → Tasks 7, 8, 9, 10, 11. ✓
- §5 reprise sans redémarrage (re-décision à chaque analyse + `_on_model_ready`) → Tasks 9-11. ✓
- §6 Modèle de décision détecteur (table) → Tasks 9, 10. ✓
- §7 Gestion erreurs (réseau, déjà en cours, total inconnu, fermeture) → Tasks 3, 5, 7. ✓
- §8 Validation via exe → Task 12. ✓

Périmètre tenu dans un seul plan cohérent ; pas de placeholder ; signatures cohérentes entre tâches
(`has_detector`, `start_model_download`, `model_ready`, `set_model_available`, `hide_degraded`,
`_request_model`, `_on_model_ready`).
