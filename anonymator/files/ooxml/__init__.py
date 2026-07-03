# Périmètre de l'anonymisation OOXML — source de vérité unique partagée
# entre l'UI (PerimetreCard) et la documentation.
COVERAGE = {
    "traite": [
        "Corps du document et paragraphes",
        "Tableaux (y compris imbriqués)",
        "En-têtes et pieds de page",
        "Zones de texte",
        "Commentaires et notes de bas de page / de fin (Word)",
        "Slides, groupes de formes et notes du présentateur (PowerPoint)",
        "Purge des métadonnées (auteur, société, dernier éditeur…)",
    ],
    "non_traite": [
        "Champs calculés et insertions automatiques",
        "Équations",
        "Texte à l'intérieur des images (pas d'OCR)",
        "Données de graphiques liées à un fichier externe",
        "Diagrammes SmartArt",
    ],
}
