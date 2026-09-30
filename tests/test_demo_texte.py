"""Le texte de démonstration du module Texte doit rester démonstratif.

`exemples/texte_demo.txt` est le seul exemple destiné au module Texte — le
premier écran de l'accueil. Un récit court qui glisse, l'air de rien, les
catégories qu'un utilisateur rencontre vraiment : nom, adresse, code postal,
téléphone, numéro de sécurité sociale, identifiant, mot de passe, IBAN, BIC.

Les tests ci-dessous vérifient qu'il fait effet **sans le modèle GLiNER** :
c'est l'état d'un utilisateur qui vient d'installer l'application et n'a pas
téléchargé les 2,2 Go. S'il ne voyait rien se passer, la démonstration se
retournerait contre le produit.
"""
from pathlib import Path

from anonymator.core.chunking import detect_long
from anonymator.ner import NullNer
from anonymator.referential import Referential

TEXTE = Path("exemples/texte_demo.txt")


def _entites():
    contenu = TEXTE.read_text(encoding="utf-8")
    return detect_long(contenu, NullNer(), Referential.load_default())


def test_le_texte_de_demonstration_est_livre():
    assert TEXTE.exists()
    assert TEXTE.stat().st_size > 500


def test_les_regles_seules_couvrent_sept_categories():
    """Sans le modèle : ce que l'application trouve dès la première minute."""
    types = {e.type for e in _entites()}
    attendus = {"ADDRESS", "IBAN", "LOGIN", "NIR",
                "PASSWORD", "PHONE", "POSTAL_CODE"}
    assert attendus <= types, f"manquants : {sorted(attendus - types)}"


def test_le_texte_illustre_aussi_les_cles_non_conformes():
    """Une partie des valeurs porte une clé de contrôle fausse : l'application
    les signale en pointillé et les laisse **décochées**.

    Ce n'est pas un défaut du jeu d'essai, c'est le comportement le plus
    déroutant de l'outil — autant que l'utilisateur le rencontre sur un exemple
    plutôt que sur son propre fichier. Si un jour ces valeurs devenaient toutes
    valides, ce cas ne serait plus démontré nulle part."""
    non_confirmees = {e.type for e in _entites() if not e.confirmed}
    assert non_confirmees, (
        "le jeu d'essai doit conserver au moins une valeur à clé fausse")


def test_aucune_donnee_reelle_n_est_promise():
    """Garde-fou de bon sens : le fichier est distribué à tous les
    utilisateurs, il ne doit contenir que des données inventées."""
    contenu = TEXTE.read_text(encoding="utf-8")
    assert "Claire Martin" in contenu      # personnage fictif du récit
    assert "@" not in contenu              # aucune adresse e-mail réelle
