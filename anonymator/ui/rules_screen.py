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
