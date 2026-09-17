# Périmètre de l'anonymisation — source de vérité unique partagée entre l'UI
# (PerimetreCard), la documentation et les tests de non-régression.
#
# Cette liste est une promesse faite à l'utilisateur : il lit « traité » et
# transmet le fichier. Un élément n'y figure donc que si un test le vérifie sur
# un fichier piégé (cf. tests/test_perimetre_tenu.py). Annoncer plus que ce que
# le code fait est pire que ne rien annoncer : cela transforme une lacune en
# fausse assurance.

_DOC_NON_TRAITE = [
    "Objets incorporés (classeur ou document inséré dans la page)",
    "Équations",
    "Texte à l'intérieur des images (pas d'OCR)",
    "Données de graphiques liées à un fichier externe",
    "Diagrammes SmartArt",
]

COVERAGE_DOCX = {
    "traite": [
        "Corps du document et paragraphes",
        "Liens hypertexte : texte affiché et adresse cible",
        "Contrôles de contenu (formulaires, modèles)",
        "Tableaux (y compris imbriqués et cellules fusionnées)",
        "En-têtes et pieds de page, y compris 1re page et pages paires",
        "Zones de texte",
        "Commentaires et notes de bas de page / de fin",
        "Texte supprimé en révision suivie",
        "Instructions de champ (publipostage, liens)",
        "Données XML liées aux contrôles de contenu",
        "Noms des auteurs de révisions et de commentaires",
        "Purge des métadonnées (auteur, société, dernier éditeur…)",
    ],
    "non_traite": list(_DOC_NON_TRAITE),
}

COVERAGE_PPTX = {
    "traite": [
        "Diapositives, groupes de formes et tableaux",
        "Notes du présentateur",
        "Masques et dispositions",
        "Adresse cible des liens hypertexte",
        "Données XML liées",
        "Noms des auteurs de commentaires",
        "Purge des métadonnées (auteur, société, dernier éditeur…)",
    ],
    "non_traite": list(_DOC_NON_TRAITE),
}

COVERAGE_XLSX = {
    "traite": [
        "Cellules de toutes les feuilles, y compris masquées",
        "Ligne d'en-tête",
        "Colonnes hors périmètre : lues sans le modèle, motifs sûrs masqués",
        "Commentaires de cellule et nom de leur auteur",
        "En-têtes et pieds de page de feuille",
        "Noms définis",
        "Textes entre guillemets d'une formule",
        "Retrait du cache des tableaux croisés dynamiques",
        "Purge des métadonnées (auteur, titre, dernier éditeur…)",
    ],
    "non_traite": [
        "Objets incorporés et images",
        "Texte à l'intérieur des images (pas d'OCR)",
        "Connexions de données externes",
        "Graphiques liés à un fichier externe",
    ],
}

COVERAGE_BY_FORMAT = {
    "docx": COVERAGE_DOCX,
    "pptx": COVERAGE_PPTX,
    "xlsx": COVERAGE_XLSX,
}

# Compatibilité : le périmètre du traitement documentaire reste accessible sous
# son ancien nom.
COVERAGE = COVERAGE_DOCX
