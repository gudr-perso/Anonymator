import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QLineEdit,
                               QTableWidget, QHeaderView, QAbstractItemView)
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.nav_band import NavBand
from anonymator.ui.components.cards import Card
from anonymator.ui.theme import color
from anonymator.user_rules import UserRules, Rule, compile_pattern


class RulesScreen(QWidget):
    def __init__(self, rules_path: Path | None, on_apply, on_back):
        super().__init__()
        self.rules_path = rules_path
        self.on_apply = on_apply
        self.user_rules = UserRules.load(rules_path) if rules_path else UserRules([])

        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(HeaderBand())
        root.addWidget(NavBand("Gestion des règles", "layers", on_home=on_back))
        body = QVBoxLayout(); body.setContentsMargins(40, 24, 40, 16); body.setSpacing(16)
        wrap = QWidget(); wrap.setLayout(body); root.addWidget(wrap)

        title = QLabel("Règles métier"); title.setObjectName("title")
        help_rules = QLabel(
            "Définissez vos propres règles. « Ne jamais masquer » protège une "
            "codification interne (ex. A####### = A + 7 chiffres, FACT.* = "
            "convention de nommage). « Toujours masquer » remplace par "
            "[REGLE-INTERNE]. Mode simple : # = un chiffre, ? = un caractère, "
            "* = n'importe quoi. Mode expert : expression régulière.")
        help_rules.setWordWrap(True); help_rules.setObjectName("muted")
        body.addWidget(title); body.addWidget(help_rules)

        # --- Carte barre d'ajout ---
        add_card = Card("sparkle", "Nouvelle règle")
        add_row = QHBoxLayout()
        self.rule_pattern = QLineEdit(); self.rule_pattern.setPlaceholderText("Motif, ex. A#######")
        self.rule_mode = QComboBox(); self.rule_mode.addItems(["simple", "expert"])
        self.rule_action = QComboBox(); self.rule_action.addItems(["Ne jamais masquer", "Toujours masquer"])
        self.rule_note = QLineEdit(); self.rule_note.setPlaceholderText("Note (optionnel)")
        btn_add_rule = QPushButton("+ Ajouter"); btn_add_rule.setObjectName("primary")
        btn_add_rule.clicked.connect(self._on_add_rule_clicked)
        for w in (self.rule_pattern, self.rule_mode, self.rule_action, self.rule_note, btn_add_rule):
            add_row.addWidget(w)
        add_card.body.addLayout(add_row)
        self.rule_error = QLabel(""); self.rule_error.setObjectName("muted")
        add_card.body.addWidget(self.rule_error)
        body.addWidget(add_card)

        # --- Carte table ---
        table_card = Card("layers", "Règles définies")
        self.count_badge = QLabel(""); self.count_badge.setObjectName("occBadge")
        table_card.head.addWidget(self.count_badge)
        self.rules_table = QTableWidget(0, 5)
        self.rules_table.setHorizontalHeaderLabels(["MOTIF", "MODE", "ACTION", "NOTE", ""])
        self.rules_table.verticalHeader().setVisible(False)
        self.rules_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rules_table.setSelectionMode(QAbstractItemView.NoSelection)
        hh = self.rules_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        # Colonne ACTION : largeur fixe calculée depuis le badge le plus long
        # (« Ne jamais masquer »). ResizeToContents ignore les widgets de
        # cellule selon l'environnement, ce qui rognait la pastille.
        from anonymator.ui.components.rule_action_badge import RuleActionBadge
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        self.rules_table.setColumnWidth(2, RuleActionBadge("keep").sizeHint().width() + 24)
        table_card.body.addWidget(self.rules_table)
        body.addWidget(table_card)

        # --- Pied ---
        path_row = QHBoxLayout()
        self.rules_path_label = QLabel(
            f"Fichier des règles : {self.rules_path}" if self.rules_path
            else "Fichier des règles : (non défini)")
        self.rules_path_label.setObjectName("muted"); self.rules_path_label.setWordWrap(True)
        btn_open = QPushButton("Ouvrir le dossier"); btn_open.setObjectName("ghost")
        btn_open.clicked.connect(self._open_rules_folder)
        path_row.addWidget(self.rules_path_label); path_row.addStretch(); path_row.addWidget(btn_open)
        body.addLayout(path_row)
        self._reload_rules()

    def _reload_rules(self):
        from PySide6.QtWidgets import QTableWidgetItem, QPushButton, QWidget, QHBoxLayout
        from PySide6.QtCore import Qt
        from anonymator.ui.components.rule_action_badge import RuleActionBadge
        from anonymator.ui.icons import icon
        self.rules_table.setRowCount(0)
        for r in self.user_rules.rules:
            row = self.rules_table.rowCount()
            self.rules_table.insertRow(row)
            self.rules_table.setItem(row, 0, QTableWidgetItem(r.pattern))
            mode_lbl = "SIMPLE" if r.mode == "simple" else "EXPERT"
            self.rules_table.setItem(row, 1, QTableWidgetItem(mode_lbl))
            badge_cell = QWidget(); bl = QHBoxLayout(badge_cell)
            bl.setContentsMargins(8, 4, 8, 4); bl.setSpacing(0)
            bl.addWidget(RuleActionBadge(r.action), 0, Qt.AlignLeft | Qt.AlignVCenter)
            bl.addStretch()
            self.rules_table.setCellWidget(row, 2, badge_cell)
            self.rules_table.setItem(row, 3, QTableWidgetItem(r.note or ""))
            btn = QPushButton(); btn.setObjectName("ghost"); btn.setFixedWidth(34)
            btn.setIcon(icon("trash", color("text_muted"), 16))
            btn.clicked.connect(lambda _=False, rule=r: self.remove_rule(rule))
            self.rules_table.setCellWidget(row, 4, btn)
        self.count_badge.setText(f"{len(self.user_rules.rules)} règles")
        self.rules_table.resizeRowsToContents()

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
