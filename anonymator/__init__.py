"""Anonymator — anonymisation locale de texte et de fichiers.

Source de vérité unique de la version du paquet. Lue au runtime par l'UI
(écran « À propos ») sans dépendance à git — l'exe PyInstaller gelé n'a pas
accès au dépôt. Ne bumper qu'au moment d'une release (cf. docs/RELEASE.md).
"""

__version__ = "0.3.0"
