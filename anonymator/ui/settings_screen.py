import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QLineEdit, QFileDialog,
                               QListWidget, QListWidgetItem, QScrollArea, QProgressBar)
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.toggle import ToggleSwitch
from anonymator.referential import Referential
from anonymator.core.model_status import is_model_available, installed_size
from anonymator.ui.download_worker import DownloadWorker
from anonymator.ui.about import about_lines
from anonymator.user_rules import UserRules, Rule, compile_pattern

_TYPES = ["PERSON", "ADDRESS", "ORG", "EMAIL", "PHONE", "IBAN", "BIC",
          "SIREN", "SIRET", "NIR", "POSTAL_CODE", "URL", "LOGIN", "PASSWORD"]


class SettingsScreen(QWidget):
    model_ready = Signal()

    def __init__(self, ref, prefs, on_apply, on_back, rules_path: Path | None = None):
        super().__init__()
        self.ref, self.prefs, self.on_apply = ref, prefs, on_apply
        self.rules_path = rules_path
        self.user_rules = UserRules.load(rules_path) if rules_path else UserRules([])
        root = QVBoxLayout(self)
        root.addWidget(HeaderBand())
        nav = QHBoxLayout()
        back = QPushButton("Accueil"); back.setObjectName("ghost"); back.clicked.connect(on_back)
        nav.addWidget(back); nav.addWidget(QLabel("Règles de détection & masquage")); nav.addStretch()
        root.addLayout(nav)

        root.addWidget(QLabel("Thème"))
        self.theme_box = QComboBox(); self.theme_box.addItems(["cuma", "cap"])
        self.theme_box.setCurrentText(prefs.theme)
        self.theme_box.currentTextChanged.connect(self.select_theme)
        root.addWidget(self.theme_box)

        root.addWidget(QLabel("Dossier de sortie"))
        row = QHBoxLayout()
        self.dir_edit = QLineEdit(prefs.output_dir or "")
        btn_dir = QPushButton("Choisir…"); btn_dir.setObjectName("secondary"); btn_dir.clicked.connect(self._choose_dir)
        row.addWidget(self.dir_edit); row.addWidget(btn_dir)
        root.addLayout(row)

        root.addWidget(QLabel("Types d'entités à détecter"))
        self._type_toggles = {}
        grid = QScrollArea(); grid.setWidgetResizable(True)
        host = QWidget(); hv = QVBoxLayout(host)
        for code in _TYPES:
            r = QHBoxLayout(); lbl = QLabel(code); tog = ToggleSwitch()
            tog.setChecked(self.ref.is_active(code))
            tog.toggled.connect(lambda on, c=code: self.set_type_active(c, on))
            r.addWidget(lbl); r.addStretch(); r.addWidget(tog)
            hv.addLayout(r); self._type_toggles[code] = tog
        grid.setWidget(host); root.addWidget(grid)

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
        root.addWidget(QLabel("À propos"))
        self.about_label = QLabel("\n".join(about_lines()))
        self.about_label.setObjectName("muted")
        self.about_label.setWordWrap(True)
        root.addWidget(self.about_label)

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
        self.model_progress.setRange(0, 0)
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

    def stop_download(self):
        """Arrête proprement le worker de téléchargement s'il tourne encore.
        Appelable depuis MainWindow (ce widget est un enfant du QStackedWidget,
        donc son closeEvent ne se déclenche pas à la fermeture de la fenêtre)."""
        if self._dl_worker is not None and self._dl_worker.isRunning():
            self._dl_worker.quit(); self._dl_worker.wait()

    def closeEvent(self, event):
        self.stop_download()
        super().closeEvent(event)

    def select_theme(self, theme: str):
        self.prefs.theme = theme
        self.on_apply()

    def set_type_active(self, code: str, active: bool):
        self.prefs.entity_overrides[code] = active
        self.on_apply()

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

    def _choose_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier de sortie")
        if path:
            self.dir_edit.setText(path); self.prefs.output_dir = path; self.on_apply()
