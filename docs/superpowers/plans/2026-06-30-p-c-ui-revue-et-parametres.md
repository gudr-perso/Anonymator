# P-C — UI revue fichier & Paramètres — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Assembler l'écran de revue fichier (vue Qt paginée, panneau typologies/valeurs, scan en thread) et l'éditeur de détection des Paramètres (toggles de types, liste d'exclusion), au-dessus de P-A et P-B.

**Architecture:** `FileScreen` devient une coquille mince à deux sous-vues (aperçu / revue) pilotée par `FileReviewSession`. Le scan tourne dans un `QThread` (`FileScanWorker`). `SettingsScreen` gagne une zone « Détection » liée à `preferences.entity_overrides` et `preferences.ner_stoplist`. `MainWindow` construit le `Referential` avec les surcharges et la stoplist des préférences et le rafraîchit à chaque changement de paramètres.

**Tech Stack:** PySide6, pytest-qt (offscreen). Dépend de **P-A** (`FileReviewSession`, `scan_csv`) et **P-B** (`Referential` overrides/stoplist, types LOGIN/PASSWORD, `confirmed`).

**Référence spec :** [2026-06-30-revue-fichier-coloree-design.md](../specs/2026-06-30-revue-fichier-coloree-design.md) §3, §6 ; [2026-06-30-qualite-detection-design.md](../specs/2026-06-30-qualite-detection-design.md) §7.

**Prérequis :** P-A et P-B présents sur `feat/revue-fichier-coloree`. Tests Qt en offscreen (déjà géré par `tests/conftest.py`). Commande : `.venv\Scripts\python.exe -m pytest -q`.

---

## Structure des fichiers (P-C)

```
anonymator/ui/preferences.py        MODIFIER : champ ner_stoplist
anonymator/ui/file_scan_worker.py   CRÉER : QThread de scan
anonymator/ui/file_screen.py        RÉÉCRIRE : aperçu colonnes + revue paginée + 2 boutons
anonymator/ui/settings_screen.py    MODIFIER : zone Détection (toggles + stoplist)
anonymator/ui/main_window.py        MODIFIER : Referential(overrides, stoplist) + refresh
tests/test_preferences.py           MODIFIER
tests/test_file_screen.py           MODIFIER
tests/test_settings_screen.py       MODIFIER
tests/test_ui_smoke.py              (inchangé, doit rester vert)
```

---

### Task 1 : `Preferences.ner_stoplist`

**Files:**
- Modify: `anonymator/ui/preferences.py`
- Test: `tests/test_preferences.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_preferences.py  (ajouter)
def test_ner_stoplist_roundtrip(tmp_path):
    from anonymator.ui.preferences import Preferences
    p = Preferences(ner_stoplist=["service client", "divers"])
    path = tmp_path / "p.json"
    p.save(path)
    loaded = Preferences.load(path)
    assert loaded.ner_stoplist == ["service client", "divers"]

def test_ner_stoplist_defaults_none(tmp_path):
    from anonymator.ui.preferences import Preferences
    assert Preferences().ner_stoplist is None
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_preferences.py -q` → FAIL.

- [ ] **Step 3 : Implémenter** — ajouter le champ et le charger

```python
@dataclass
class Preferences:
    theme: str = "cuma"
    output_dir: str | None = None
    entity_overrides: dict[str, bool] = field(default_factory=dict)
    ner_stoplist: list[str] | None = None     # None = utiliser la liste par défaut du config

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2),
                        encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Preferences":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(theme=data.get("theme", "cuma"),
                   output_dir=data.get("output_dir"),
                   entity_overrides=data.get("entity_overrides", {}),
                   ner_stoplist=data.get("ner_stoplist"))
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_preferences.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/preferences.py tests/test_preferences.py
git commit -m "feat(prefs): champ ner_stoplist (liste d'exclusion utilisateur)"
```

---

### Task 2 : `FileScanWorker` (scan en thread)

**Files:**
- Create: `anonymator/ui/file_scan_worker.py`
- Test: `tests/test_file_screen.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_file_screen.py  (ajouter en tête des imports si besoin)
from anonymator.ui.file_scan_worker import FileScanWorker
from anonymator.files import csv_io
from anonymator.files.columns import default_maskable_columns
from anonymator.referential import Referential
from anonymator.ner import FakeNer

def test_scan_worker_emits_result(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    doc = csv_io.read_csv(src)
    cols = default_maskable_columns(doc.rows, doc.has_header)
    worker = FileScanWorker(doc, FakeNer({"Claire Martin": "PERSON"}),
                            Referential.load_default(), cols)
    with qtbot.waitSignal(worker.scan_finished, timeout=5000) as blocker:
        worker.start()
    scanned = blocker.args[0]
    assert (1, 0) in scanned
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_screen.py::test_scan_worker_emits_result -q` → FAIL (module absent).

- [ ] **Step 3 : Implémenter** `anonymator/ui/file_scan_worker.py`

```python
from PySide6.QtCore import QThread, Signal
from anonymator.files.anonymize_file import scan_csv


class FileScanWorker(QThread):
    scan_finished = Signal(dict)     # {(r,c): [Entity, ...]}
    error = Signal(str)

    def __init__(self, doc, ner, ref, cols):
        super().__init__()
        self._doc, self._ner, self._ref, self._cols = doc, ner, ref, cols

    def run(self):
        try:
            self.scan_finished.emit(scan_csv(self._doc, self._ner, self._ref, self._cols))
        except Exception as exc:                      # noqa: BLE001 — remonté à l'UI
            self.error.emit(str(exc))
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_screen.py::test_scan_worker_emits_result -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/file_scan_worker.py tests/test_file_screen.py
git commit -m "feat(ui): FileScanWorker — scan CSV en thread de fond"
```

---

### Task 3 : Aperçu avec colonnes éclatées + en-têtes

**Files:**
- Modify: `anonymator/ui/file_screen.py`
- Test: `tests/test_file_screen.py`

Réécriture de l'aperçu : afficher les colonnes du CSV (en-tête comme libellés), au lieu d'un bloc.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_file_screen.py  (ajouter)
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.ui.file_screen import FileScreen

def _screen(loader_map=None):
    ref = Referential.load_default()
    loader = ModelLoader(FakeNer(loader_map or {}))
    return FileScreen(ref, loader, Preferences(), on_back=lambda: None)

def test_preview_splits_columns(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.table.columnCount() == 2
    assert s.table.horizontalHeaderItem(0).text() == "Nom"
    assert s.table.item(0, 0).text() == "Claire Martin"
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_screen.py::test_preview_splits_columns -q`
Expected : FAIL (en-têtes non posées / colonnes non séparées selon l'implémentation actuelle).

- [ ] **Step 3 : Implémenter** — réécrire `anonymator/ui/file_screen.py` (base aperçu)

```python
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem, QFileDialog,
                               QMessageBox, QTreeWidget, QTreeWidgetItem, QLineEdit)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from anonymator.files.anonymize_file import (anonymize_file, UnsupportedFormat,
                                             apply_csv)
from anonymator.files import csv_io
from anonymator.files.columns import default_maskable_columns
from anonymator.core.file_review_session import FileReviewSession
from anonymator.ui.file_scan_worker import FileScanWorker
from anonymator.ui.colors import color_for

PAGE_SIZE = 20


class FileScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back, on_text_review=None):
        super().__init__()
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.on_text_review = on_text_review
        self.path: Path | None = None
        self.doc = None
        self.session: FileReviewSession | None = None
        self.page = 0
        self._worker: FileScanWorker | None = None

        layout = QVBoxLayout(self)
        self.label = QLabel("Aucun fichier")
        self.table = QTableWidget()
        btns = QHBoxLayout()
        self.btn_open = QPushButton("Ouvrir…")
        self.btn_open.clicked.connect(self._open)
        self.btn_review = QPushButton("Analyser et revoir")
        self.btn_review.clicked.connect(self.analyze)
        self.btn_run = QPushButton("Anonymiser et enregistrer")
        self.btn_run.clicked.connect(lambda: self.run())
        self.btn_back = QPushButton("Accueil")
        self.btn_back.setObjectName("ghost")
        self.btn_back.clicked.connect(on_back)
        for b in (self.btn_open, self.btn_review, self.btn_run, self.btn_back):
            btns.addWidget(b)

        # panneau revue (typologies/valeurs) + pagination, cachés tant qu'on n'analyse pas
        self.side = QTreeWidget()
        self.side.setHeaderLabels(["Typologie / valeur", "Occ."])
        self.side.itemChanged.connect(self._on_side_changed)
        self.side.hide()
        self.pager = QHBoxLayout()
        self.btn_first = QPushButton("« Première"); self.btn_first.clicked.connect(lambda: self._go(0))
        self.btn_prev = QPushButton("‹ Préc."); self.btn_prev.clicked.connect(lambda: self._go(self.page - 1))
        self.lbl_page = QLabel("")
        self.btn_next = QPushButton("Suiv. ›"); self.btn_next.clicked.connect(lambda: self._go(self.page + 1))
        self.btn_last = QPushButton("Dernière »"); self.btn_last.clicked.connect(lambda: self._go(self._page_count() - 1))
        self.goto = QLineEdit(); self.goto.setFixedWidth(50)
        self.goto.returnPressed.connect(self._goto_typed)
        for w in (self.btn_first, self.btn_prev, self.lbl_page, self.btn_next, self.btn_last, QLabel("Aller à"), self.goto):
            self.pager.addWidget(w)
        self.pager_widget = QWidget(); self.pager_widget.setLayout(self.pager); self.pager_widget.hide()

        body = QHBoxLayout()
        body.addWidget(self.table, 3)
        body.addWidget(self.side, 1)

        layout.addWidget(self.label)
        layout.addLayout(btns)
        layout.addLayout(body)
        layout.addWidget(self.pager_widget)

    # ---------- ouverture / aperçu ----------
    def _open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir", "", "Fichiers (*.txt *.csv *.xlsx)")
        if path:
            self.load_path(path)

    def load_path(self, path: str):
        self.path = Path(path)
        self.doc = None
        self.session = None
        self.side.hide(); self.pager_widget.hide()
        self.label.setText(self.path.name)
        suffix = self.path.suffix.lower()
        self.btn_review.setEnabled(suffix == ".csv")   # revue colorée : CSV (txt → revue texte)
        if suffix == ".csv":
            self.doc = csv_io.read_csv(self.path)
            self._fill_preview(self.doc.rows[:50])

    def _fill_preview(self, rows):
        if not rows:
            return
        header = rows[0] if (self.doc and self.doc.has_header) else None
        data = rows[1:] if header else rows
        width = max(len(r) for r in rows)
        self.table.clear()
        self.table.setColumnCount(width)
        self.table.setRowCount(len(data))
        if header:
            self.table.setHorizontalHeaderLabels(
                [header[c] if c < len(header) else f"col{c}" for c in range(width)])
        for r, row in enumerate(data):
            for c in range(width):
                self.table.setItem(r, c, QTableWidgetItem(row[c] if c < len(row) else ""))

    def run(self, when: datetime | None = None):
        if not self.path:
            return None
        out_dir = Path(self.prefs.output_dir) if self.prefs.output_dir else self.path.parent
        when = when or datetime.now()
        try:
            ner = self.loader.get()
            result = anonymize_file(self.path, ner, self.ref, out_dir, when)
        except UnsupportedFormat as e:
            QMessageBox.warning(self, "Format non supporté", str(e))
            return None
        return result
```

> Les méthodes `analyze`, `_on_side_changed`, `_go`, `_goto_typed`, `_page_count`, `_render_page`
> sont ajoutées aux Tasks 4-5. Pour faire passer le test de cette task, ces connexions pointent vers
> des méthodes définies juste après — crée des stubs minimaux maintenant si tu exécutes la task
> isolément :
> ```python
>     def analyze(self): pass
>     def _on_side_changed(self, *a): pass
>     def _go(self, p): pass
>     def _goto_typed(self): pass
>     def _page_count(self): return 1
> ```
> (Ces stubs sont remplacés en Tasks 4-5.)

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_screen.py::test_preview_splits_columns -q` → PASS.
Vérifier aussi `test_run_on_csv_writes_output` (existant) → toujours PASS (signature `run(when=...)` conservée).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/file_screen.py tests/test_file_screen.py
git commit -m "feat(ui): aperçu fichier en colonnes + bouton Analyser et revoir"
```

---

### Task 4 : Mode revue — scan, panneau typologies/valeurs, rendu page

**Files:**
- Modify: `anonymator/ui/file_screen.py`
- Test: `tests/test_file_screen.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_file_screen.py  (ajouter)
def test_analyze_builds_session_and_side(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\nPaul Durand;50,00\n".encode("cp1252"))
    s = _screen({"Claire Martin": "PERSON", "Paul Durand": "PERSON"})
    qtbot.addWidget(s)
    s.load_path(str(src))
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.session.count_retained("PERSON") == 2
    assert s.side.topLevelItemCount() == 1            # un type : PERSON
    assert s.side.topLevelItem(0).childCount() == 2   # deux valeurs distinctes
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_screen.py::test_analyze_builds_session_and_side -q` → FAIL (analyze stub).

- [ ] **Step 3 : Implémenter** — remplacer les stubs par les vraies méthodes

```python
    # ---------- revue ----------
    def analyze(self):
        if self.doc is None:
            return
        cols = default_maskable_columns(self.doc.rows, self.doc.has_header)
        self._cols = cols
        self.btn_review.setEnabled(False)
        self.btn_run.setEnabled(False)
        self.label.setText(f"{self.path.name} — analyse en cours…")
        ner = self.loader.get()
        self._worker = FileScanWorker(self.doc, ner, self.ref, cols)
        self._worker.scan_finished.connect(self._on_scanned)
        self._worker.error.connect(self._on_scan_error)
        self._worker.start()

    def _on_scan_error(self, msg):
        self.btn_review.setEnabled(True); self.btn_run.setEnabled(True)
        self.label.setText(self.path.name)
        QMessageBox.warning(self, "Erreur d'analyse", msg)

    def _on_scanned(self, scanned):
        self.session = FileReviewSession(self.doc, scanned, self.ref, self._cols)
        self.btn_review.setEnabled(True); self.btn_run.setEnabled(True)
        self.label.setText(self.path.name)
        self.page = 0
        self._build_side()
        self.side.show(); self.pager_widget.show()
        self._render_page()

    def _build_side(self):
        self.side.blockSignals(True)
        self.side.clear()
        for t in self.session.types():
            top = QTreeWidgetItem([t, str(self.session.count_retained(t))])
            top.setForeground(0, QColor(color_for(t)))
            top.setData(0, Qt.UserRole, ("type", t, None))
            top.setFlags(top.flags() | Qt.ItemIsUserCheckable)
            top.setCheckState(0, Qt.Checked)
            for value, n in self.session.values_for(t):
                child = QTreeWidgetItem([value, f"×{n}"])
                child.setData(0, Qt.UserRole, ("value", t, value))
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                enabled = self.session.is_value_enabled(t, value)
                child.setCheckState(0, Qt.Checked if enabled else Qt.Unchecked)
                top.addChild(child)
            self.side.addTopLevelItem(top)
        self.side.expandAll()
        self.side.blockSignals(False)

    def _on_side_changed(self, item, _col):
        kind, etype, value = item.data(0, Qt.UserRole)
        checked = item.checkState(0) == Qt.Checked
        if kind == "type":
            self.session.set_type_enabled(etype, checked)
        else:
            self.session.set_value_enabled(etype, value, checked)
        self._refresh_counts()
        self._render_page()

    def _refresh_counts(self):
        for i in range(self.side.topLevelItemCount()):
            top = self.side.topLevelItem(i)
            _, t, _ = top.data(0, Qt.UserRole)
            top.setText(1, str(self.session.count_retained(t)))
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_screen.py::test_analyze_builds_session_and_side -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/file_screen.py tests/test_file_screen.py
git commit -m "feat(ui): mode revue — scan threadé, panneau typologies/valeurs"
```

---

### Task 5 : Pagination & surlignage de page

**Files:**
- Modify: `anonymator/ui/file_screen.py`
- Test: `tests/test_file_screen.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_file_screen.py  (ajouter)
def test_pagination_navigates(qtbot, tmp_path):
    lines = "Nom;Montant\n" + "".join(f"Nom{i};1,00\n" for i in range(45))
    src = tmp_path / "big.csv"; src.write_bytes(lines.encode("cp1252"))
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s._page_count() == 3            # 45 lignes / 20
    s._go(99)                              # borné à la dernière
    assert s.page == 2
    assert s.table.rowCount() == 5         # 45 - 40
    s._go(0)
    assert s.table.rowCount() == 20
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_screen.py::test_pagination_navigates -q` → FAIL.

- [ ] **Step 3 : Implémenter** — pagination + rendu coloré de la page

```python
    def _data_rows(self):
        start = 1 if self.doc.has_header else 0
        return list(range(start, len(self.doc.rows)))

    def _page_count(self):
        n = len(self._data_rows())
        return max(1, (n + PAGE_SIZE - 1) // PAGE_SIZE)

    def _go(self, page):
        self.page = max(0, min(page, self._page_count() - 1))
        self._render_page()

    def _goto_typed(self):
        try:
            self._go(int(self.goto.text()) - 1)
        except ValueError:
            pass

    def _render_page(self):
        if self.session is None:
            return
        rows = self._data_rows()
        width = max(len(r) for r in self.doc.rows)
        page_rows = rows[self.page * PAGE_SIZE:(self.page + 1) * PAGE_SIZE]
        header = self.doc.rows[0] if self.doc.has_header else None
        self.table.clear()
        self.table.setColumnCount(width)
        self.table.setRowCount(len(page_rows))
        if header:
            self.table.setHorizontalHeaderLabels(
                [header[c] if c < len(header) else f"col{c}" for c in range(width)])
        for vr, r in enumerate(page_rows):
            retained_cols = {c: self.session.entities_for_cell(r, c) for c in range(width)}
            for c in range(width):
                val = self.doc.rows[r][c] if c < len(self.doc.rows[r]) else ""
                item = QTableWidgetItem(val)
                ents = retained_cols.get(c) or []
                if ents:
                    col = QColor(color_for(ents[0].type)); col.setAlpha(70)
                    item.setBackground(col)
                self.table.setItem(vr, c, item)
        self.lbl_page.setText(f"page {self.page + 1} / {self._page_count()}")
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_screen.py::test_pagination_navigates -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/file_screen.py tests/test_file_screen.py
git commit -m "feat(ui): pagination 20 lignes + surlignage par typologie"
```

---

### Task 6 : Appliquer la revue & enregistrer

**Files:**
- Modify: `anonymator/ui/file_screen.py`
- Test: `tests/test_file_screen.py`

Quand une session de revue est active, « Anonymiser et enregistrer » écrit le **document masqué de la session** (décisions utilisateur) plutôt que de tout re-masquer.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_file_screen.py  (ajouter)
from datetime import datetime
from anonymator.ui.preferences import Preferences

def test_apply_review_writes_user_choices(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\nPaul Durand;50,00\n".encode("cp1252"))
    ref = Referential.load_default()
    from anonymator.ui.model_loader import ModelLoader
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON", "Paul Durand": "PERSON"}))
    s = FileScreen(ref, loader, Preferences(output_dir=str(tmp_path)), on_back=lambda: None)
    qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    s.session.set_value_enabled("PERSON", "Paul Durand", False)   # garder Paul en clair
    res = s.run(when=datetime(2026, 1, 2, 3, 4, 5))
    out = res.output_path.read_bytes().decode("cp1252")
    assert "[PERSONNE]" in out and "Paul Durand" in out and "Claire Martin" not in out
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_screen.py::test_apply_review_writes_user_choices -q` → FAIL (run ignore la session).

- [ ] **Step 3 : Implémenter** — brancher `run()` sur la session si présente

```python
    def run(self, when: datetime | None = None):
        if not self.path:
            return None
        out_dir = Path(self.prefs.output_dir) if self.prefs.output_dir else self.path.parent
        when = when or datetime.now()
        if self.session is not None:
            from anonymator.output_naming import anonymized_path
            masked = self.session.masked_document()
            report = self.session.report()
            out = anonymized_path(self.path, out_dir, when)
            csv_io.write_csv(masked, out)
            from anonymator.files.anonymize_file import FileResult
            return FileResult(out, report)
        try:
            ner = self.loader.get()
            result = anonymize_file(self.path, ner, self.ref, out_dir, when)
        except UnsupportedFormat as e:
            QMessageBox.warning(self, "Format non supporté", str(e))
            return None
        return result
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_screen.py -q` → PASS (toute la classe). Suite complète → verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/file_screen.py tests/test_file_screen.py
git commit -m "feat(ui): Appliquer et enregistrer respecte les choix de revue"
```

---

### Task 7 : Routage txt → revue texte ; xlsx désactivé

**Files:**
- Modify: `anonymator/ui/file_screen.py` (`load_path`), `anonymator/ui/main_window.py`
- Test: `tests/test_file_screen.py`

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_file_screen.py  (ajouter)
def test_review_disabled_for_xlsx(qtbot, tmp_path):
    src = tmp_path / "f.xlsx"; src.write_bytes(b"PK\x03\x04stub")   # extension xlsx
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.btn_review.isEnabled() is False

def test_txt_routes_to_text_review(qtbot, tmp_path):
    called = {}
    ref = Referential.load_default()
    from anonymator.ui.model_loader import ModelLoader
    from anonymator.ui.preferences import Preferences
    s = FileScreen(ref, ModelLoader(FakeNer({})), Preferences(),
                   on_back=lambda: None,
                   on_text_review=lambda text: called.setdefault("text", text))
    qtbot.addWidget(s)
    src = tmp_path / "n.txt"; src.write_text("Bonjour Claire", encoding="utf-8")
    s.load_path(str(src))
    s.analyze()
    assert called.get("text") == "Bonjour Claire"
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_screen.py::test_txt_routes_to_text_review -q` → FAIL.

- [ ] **Step 3 : Implémenter**

Dans `load_path`, activer le bouton revue pour csv **et** txt, et dans `analyze` router le txt :

```python
    def load_path(self, path: str):
        self.path = Path(path)
        self.doc = None
        self.session = None
        self.side.hide(); self.pager_widget.hide()
        self.label.setText(self.path.name)
        suffix = self.path.suffix.lower()
        self.btn_review.setEnabled(suffix in (".csv", ".txt"))
        if suffix == ".csv":
            self.doc = csv_io.read_csv(self.path)
            self._fill_preview(self.doc.rows[:50])
```

```python
    def analyze(self):
        if self.path and self.path.suffix.lower() == ".txt":
            from anonymator.files import txt_io
            text, _enc = txt_io.read_text(self.path)
            if self.on_text_review:
                self.on_text_review(text)
            return
        if self.doc is None:
            return
        # ... (suite CSV inchangée : cols, worker, etc.)
```

Dans `anonymator/ui/main_window.py`, passer un callback qui ouvre l'écran texte pré-rempli :

```python
        self.file_screen = FileScreen(self.ref, self.loader, self.prefs,
                                      self.show_home, on_text_review=self._review_text)
```

et ajouter la méthode :

```python
    def _review_text(self, text: str):
        self.text_screen.input.setPlainText(text)
        self.stack.setCurrentWidget(self.text_screen)
        self.text_screen.analyze()
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_screen.py tests/test_ui_smoke.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/file_screen.py anonymator/ui/main_window.py tests/test_file_screen.py
git commit -m "feat(ui): txt routé vers la revue texte, revue désactivée pour xlsx"
```

---

### Task 8 : Paramètres — toggles de types d'entités

**Files:**
- Modify: `anonymator/ui/settings_screen.py`
- Test: `tests/test_settings_screen.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_settings_screen.py  (ajouter)
def test_toggle_entity_type_updates_overrides(qtbot):
    from anonymator.referential import Referential
    from anonymator.ui.preferences import Preferences
    from anonymator.ui.settings_screen import SettingsScreen
    prefs = Preferences()
    called = []
    s = SettingsScreen(Referential.load_default(), prefs,
                       on_apply=lambda: called.append(True), on_back=lambda: None)
    qtbot.addWidget(s)
    s.set_type_active("BIC", True)
    assert prefs.entity_overrides["BIC"] is True
    assert called
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_settings_screen.py::test_toggle_entity_type_updates_overrides -q` → FAIL.

- [ ] **Step 3 : Implémenter** — ajouter une zone « Détection : types » avec des cases

Ajouter dans `SettingsScreen.__init__` (après le dossier de sortie, avant `back`), et la méthode `set_type_active`. Importer `QCheckBox` :

```python
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QLineEdit, QFileDialog, QCheckBox)
```

```python
        layout.addWidget(QLabel("Détection — types d'entités"))
        self._type_boxes = {}
        for code in ["PERSON", "ADDRESS", "ORG", "EMAIL", "PHONE", "IBAN", "BIC",
                     "SIREN", "SIRET", "NIR", "POSTAL_CODE", "URL", "LOGIN", "PASSWORD"]:
            cb = QCheckBox(code)
            cb.setChecked(self.ref.is_active(code))
            cb.toggled.connect(lambda checked, c=code: self.set_type_active(c, checked))
            layout.addWidget(cb)
            self._type_boxes[code] = cb
```

```python
    def set_type_active(self, code: str, active: bool):
        self.prefs.entity_overrides[code] = active
        self.on_apply()
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_settings_screen.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/settings_screen.py tests/test_settings_screen.py
git commit -m "feat(settings): toggles d'activation des types d'entités"
```

---

### Task 9 : Paramètres — éditeur de liste d'exclusion

**Files:**
- Modify: `anonymator/ui/settings_screen.py`
- Test: `tests/test_settings_screen.py`

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_settings_screen.py  (ajouter)
def test_add_and_remove_stoplist_term(qtbot):
    from anonymator.referential import Referential
    from anonymator.ui.preferences import Preferences
    from anonymator.ui.settings_screen import SettingsScreen
    prefs = Preferences()
    s = SettingsScreen(Referential.load_default(), prefs,
                       on_apply=lambda: None, on_back=lambda: None)
    qtbot.addWidget(s)
    s.add_stop_term("service client")
    assert "service client" in prefs.ner_stoplist
    s.remove_stop_term("service client")
    assert "service client" not in prefs.ner_stoplist
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_settings_screen.py::test_add_and_remove_stoplist_term -q` → FAIL.

- [ ] **Step 3 : Implémenter** — éditeur liste (champ + Ajouter, et liste avec ✕)

Importer `QListWidget`, `QListWidgetItem`. Ajouter dans `__init__` :

```python
        layout.addWidget(QLabel("Détection — liste d'exclusion (NER)"))
        from anonymator.referential import Referential as _Ref
        # liste effective : préférences si définies, sinon défaut du config
        base = self.prefs.ner_stoplist
        if base is None:
            base = sorted(_Ref.load_default().ner_stoplist())
        self.prefs.ner_stoplist = list(base)
        add_row = QHBoxLayout()
        self.stop_edit = QLineEdit()
        btn_add = QPushButton("Ajouter")
        btn_add.clicked.connect(lambda: self.add_stop_term(self.stop_edit.text().strip()))
        add_row.addWidget(self.stop_edit); add_row.addWidget(btn_add)
        layout.addLayout(add_row)
        self.stop_list = QListWidget()
        layout.addWidget(self.stop_list)
        self._reload_stoplist()
```

et les méthodes :

```python
    def _reload_stoplist(self):
        self.stop_list.clear()
        for term in self.prefs.ner_stoplist:
            row = QWidget(); h = QHBoxLayout(row); h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(QLabel(term))
            x = QPushButton("✕"); x.setFixedWidth(28)
            x.clicked.connect(lambda _=False, t=term: self.remove_stop_term(t))
            h.addWidget(x)
            from PySide6.QtWidgets import QListWidgetItem
            it = QListWidgetItem(); it.setSizeHint(row.sizeHint())
            self.stop_list.addItem(it); self.stop_list.setItemWidget(it, row)

    def add_stop_term(self, term: str):
        if term and term not in self.prefs.ner_stoplist:
            self.prefs.ner_stoplist.append(term)
            self.stop_edit.clear()
            self._reload_stoplist()
            self.on_apply()

    def remove_stop_term(self, term: str):
        if term in self.prefs.ner_stoplist:
            self.prefs.ner_stoplist.remove(term)
            self._reload_stoplist()
            self.on_apply()
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_settings_screen.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/settings_screen.py tests/test_settings_screen.py
git commit -m "feat(settings): éditeur de liste d'exclusion (ajout/suppression)"
```

---

### Task 10 : `MainWindow` — Referential branché sur préférences + refresh

**Files:**
- Modify: `anonymator/ui/main_window.py`
- Test: `tests/test_ui_smoke.py`

Construire le `Referential` avec les surcharges + la stoplist des préférences, et le reconstruire quand les Paramètres changent (pour que toggles et stoplist prennent effet sans redémarrer).

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_ui_smoke.py  (ajouter)
def test_referential_uses_prefs_overrides(qtbot, tmp_path):
    from anonymator.ui.main_window import MainWindow
    from anonymator.ui.model_loader import ModelLoader
    from anonymator.ner import FakeNer
    prefs_path = tmp_path / "prefs.json"
    (tmp_path).mkdir(exist_ok=True)
    prefs_path.write_text('{"theme":"cuma","entity_overrides":{"BIC":true},'
                          '"ner_stoplist":["truc"]}', encoding="utf-8")
    win = MainWindow(loader=ModelLoader(FakeNer({})), prefs_path=prefs_path)
    qtbot.addWidget(win)
    assert win.ref.is_active("BIC") is True
    assert "truc" in win.ref.ner_stoplist()
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_ui_smoke.py::test_referential_uses_prefs_overrides -q` → FAIL.

- [ ] **Step 3 : Implémenter** — dans `MainWindow.__init__`, construire le ref depuis les prefs ; rebâtir au `_apply_prefs`

Remplacer la ligne `self.ref = Referential.load_default()` par un helper, et l'appeler aussi dans `_apply_prefs` :

```python
    def _build_ref(self):
        ref = Referential.load_default(overrides=self.prefs.entity_overrides)
        if self.prefs.ner_stoplist is not None:
            ref = ref.with_stoplist(self.prefs.ner_stoplist)
        return ref
```

Dans `__init__` (avant la création des écrans) :

```python
        self.prefs = Preferences.load(prefs_path)
        self.ref = self._build_ref()
```

Dans `_apply_prefs`, rafraîchir le ref et le propager aux écrans :

```python
    def _apply_prefs(self):
        self.prefs.save(self.prefs_path)
        self.ref = self._build_ref()
        self.text_screen.ref = self.ref
        self.file_screen.ref = self.ref
        self._apply_theme()
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_ui_smoke.py -q` → PASS. Suite complète `.venv\Scripts\python.exe -m pytest -q` → verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/main_window.py tests/test_ui_smoke.py
git commit -m "feat(ui): Referential piloté par les préférences + refresh au changement"
```

---

## Auto-revue (P-C vs specs)

- Revue §3 deux boutons (direct + « Analyser et revoir »), scan threadé → Tasks 2-4. ✓
- Revue §6 pagination 20 lignes, première/préc./suiv./dernière + aller à, surlignage par type,
  rendu page courante seule → Task 5. ✓
- Revue §2 txt → revue texte ; xlsx désactivé → Task 7. ✓
- Revue : appliquer respecte les décisions utilisateur → Task 6. ✓
- Détection §7 toggles types (BIC/CP/URL…) + éditeur stoplist + persistance prefs + branchement
  Referential → Tasks 1, 8, 9, 10. ✓

**Écart d'implémentation à valider** : les cases inclure/exclure **colonnes** de la maquette (dans
l'en-tête) ne sont pas encore câblées ici (le panneau gère type/valeur ; `FileReviewSession`
supporte déjà `set_column_enabled`). À ajouter en finition — soit en en-tête cliquable, soit en
rangée de cases au-dessus du tableau. Tâche de polissage non bloquante pour le parcours principal.
```
