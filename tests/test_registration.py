"""Invitation à s'enregistrer au lancement.

Deux promesses sont tenues ici :
- **non bloquant** : l'utilisateur peut toujours refuser, et on n'insiste pas
  (deux invitations au plus) ;
- **aucun appel réseau** : l'application se contente d'ouvrir le formulaire
  dans le navigateur. La promesse « aucune donnée ne quitte votre machine »
  reste donc vraie mot pour mot.
"""
import ast
from pathlib import Path

import pytest

from anonymator import brand
from anonymator.brand import lock_brand, reset_brand
from anonymator.ui import registration as reg
from anonymator.ui.preferences import Preferences


def teardown_function():
    reset_brand()


class _FakeDialog:
    """Remplace le QDialog : renvoie un choix scripté et compte les affichages."""
    def __init__(self, choice):
        self.choice = choice
        self.shown = 0

    def __call__(self, parent):
        self.shown += 1
        return self.choice


def _run(prefs, choice, opened=None, saves=None):
    dlg = _FakeDialog(choice)
    reg.maybe_prompt(None, prefs,
                     save=lambda: saves.append(True) if saves is not None else None,
                     open_url=lambda url: opened.append(url) if opened is not None else None,
                     ask=dlg)
    return dlg


# --- Politique d'affichage ----------------------------------------------

def test_premier_lancement_propose_l_enregistrement():
    p = Preferences()
    assert _run(p, reg.LATER).shown == 1


def test_plus_tard_redemande_au_cinquieme_lancement_puis_plus_jamais():
    p = Preferences()
    affichages = [_run(p, reg.LATER).shown for _ in range(12)]
    assert affichages[0] == 1 and affichages[4] == 1
    assert sum(affichages) == 2


def test_ne_plus_demander_est_definitif():
    p = Preferences()
    _run(p, reg.NEVER)
    assert p.registration == "never"
    assert sum(_run(p, reg.LATER).shown for _ in range(10)) == 0


def test_apres_enregistrement_on_ne_redemande_plus():
    p = Preferences()
    _run(p, reg.REGISTER, opened=[])
    assert p.registration == "done"
    assert sum(_run(p, reg.LATER).shown for _ in range(10)) == 0


def test_m_enregistrer_ouvre_le_formulaire_dans_le_navigateur():
    opened = []
    _run(Preferences(), reg.REGISTER, opened=opened)
    assert opened == [brand.CAP_FORM_URL]


def test_plus_tard_et_refus_n_ouvrent_rien():
    opened = []
    _run(Preferences(), reg.LATER, opened=opened)
    _run(Preferences(), reg.NEVER, opened=opened)
    assert opened == []


def test_le_choix_est_sauvegarde():
    saves = []
    _run(Preferences(), reg.NEVER, saves=saves)
    assert saves


def test_etat_persiste_entre_deux_lancements(tmp_path):
    path = tmp_path / "prefs.json"
    p = Preferences()
    reg.maybe_prompt(None, p, save=lambda: p.save(path), open_url=lambda u: None,
                     ask=_FakeDialog(reg.NEVER))
    assert Preferences.load(path).registration == "never"


def test_preferences_anciennes_sans_champ_enregistrement(tmp_path):
    """Mise à jour d'une install existante : le fichier ne connaît pas les
    nouveaux champs → on propose, comme à un premier lancement."""
    path = tmp_path / "prefs.json"
    path.write_text('{"theme": "cap"}', encoding="utf-8")
    p = Preferences.load(path)
    assert p.registration == "pending" and p.launch_count == 0
    assert _run(p, reg.LATER).shown == 1


# --- Aucun appel réseau ---------------------------------------------------

_NETWORK_MODULES = {"socket", "urllib", "http", "httpx", "requests", "aiohttp",
                    "huggingface_hub", "ssl", "QtNetwork"}


def test_le_module_n_importe_aucune_bibliotheque_reseau():
    tree = ast.parse(Path(reg.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported |= {a.name for a in node.names}
    parts = {seg for name in imported for seg in name.split(".")}
    assert not parts & _NETWORK_MODULES


@pytest.mark.parametrize("key", sorted(brand.BRANDS))
def test_les_url_sont_des_constantes_https_sans_donnee_utilisateur(key):
    url = brand.BRANDS[key].form_url
    assert url is None or (url.startswith("https://") and "{" not in url)


# --- Un formulaire par édition --------------------------------------------

@pytest.mark.parametrize("key", sorted(brand.BRANDS))
def test_chaque_edition_ouvre_son_propre_formulaire(key, monkeypatch):
    from dataclasses import replace
    url = f"https://example.com/form-{key}"
    monkeypatch.setitem(brand.BRANDS, key, replace(brand.BRANDS[key], form_url=url))
    lock_brand(key)
    opened = []
    _run(Preferences(), reg.REGISTER, opened=opened)
    assert opened == [url]


def test_edition_sans_formulaire_ne_propose_rien(monkeypatch):
    from dataclasses import replace
    monkeypatch.setitem(brand.BRANDS, "cuma", replace(brand.BRANDS["cuma"], form_url=None))
    lock_brand("cuma")
    p = Preferences()
    assert sum(_run(p, reg.REGISTER).shown for _ in range(6)) == 0
    assert p.registration == "pending" and p.launch_count == 0


# --- Dialogue réel ---------------------------------------------------------

@pytest.mark.parametrize("btn, attendu", [("register_btn", reg.REGISTER),
                                          ("later_btn", reg.LATER),
                                          ("never_btn", reg.NEVER)])
def test_boutons_du_dialogue(qtbot, btn, attendu):
    dlg = reg.RegistrationDialog()
    qtbot.addWidget(dlg)
    getattr(dlg, btn).click()
    assert dlg.choice == attendu


def test_fermer_la_fenetre_vaut_plus_tard(qtbot):
    dlg = reg.RegistrationDialog()
    qtbot.addWidget(dlg)
    dlg.reject()
    assert dlg.choice == reg.LATER


def test_le_dialogue_rassure_sur_les_donnees(qtbot):
    from PySide6.QtWidgets import QLabel
    dlg = reg.RegistrationDialog()
    qtbot.addWidget(dlg)
    texte = " ".join(l.text() for l in dlg.findChildren(QLabel))
    assert "restent sur votre poste" in texte
    assert "gratuit" in texte


# --- Intégration fenêtre principale ---------------------------------------

def test_fenetre_principale_sauvegarde_le_choix(qtbot, tmp_path, monkeypatch):
    from unittest.mock import patch
    from anonymator.ui.main_window import MainWindow
    monkeypatch.setattr(reg, "_ask_with_dialog", lambda parent: reg.NEVER)
    path = tmp_path / "prefs.json"
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        win = MainWindow(prefs_path=path)
    qtbot.addWidget(win)
    win.offer_registration()
    qtbot.waitUntil(lambda: path.exists())
    assert Preferences.load(path).registration == "never"


@pytest.mark.parametrize("theme", ["cap", "cuma"])
def test_aucun_paragraphe_n_est_coupe(qtbot, theme):
    """Le thème (polices) est appliqué par la fenêtre parente à l'affichage :
    chaque paragraphe doit alors avoir la hauteur de toutes ses lignes."""
    from PySide6.QtWidgets import QLabel, QMainWindow
    from anonymator.ui.theme import build_qss, set_active_theme
    lock_brand(theme)
    set_active_theme(theme)
    parent = QMainWindow(); parent.setStyleSheet(build_qss(theme))
    qtbot.addWidget(parent); parent.show()
    dlg = reg.RegistrationDialog(parent)
    dlg.show(); qtbot.waitExposed(dlg)
    for l in dlg.findChildren(QLabel):
        if l.wordWrap():
            assert l.height() >= l.heightForWidth(l.width()), l.text()[:30]
