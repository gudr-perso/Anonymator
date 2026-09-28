# Périmètre de l'anonymisation d'une image — source de vérité unique partagée
# entre l'UI (PerimetreCard), la documentation et les tests.
#
# Même règle que pour les documents : un élément ne figure en « traité » que si
# un test le vérifie. Ici s'ajoute une contrainte propre à l'OCR — il rate. La
# formulation dit donc que l'application PROPOSE et que l'utilisateur VALIDE ;
# elle ne dit jamais que l'image « a été analysée ».

COVERAGE_IMAGE = {
    "traite": [
        "Texte lu par la reconnaissance de caractères, proposé à votre validation",
        "Zones que vous tracez vous-même à la souris",
        "Destruction réelle des pixels (la zone noircie est irrécupérable)",
        "Purge des métadonnées EXIF (position GPS, appareil, auteur, date)",
    ],
    "non_traite": [
        "Texte que la reconnaissance n'a pas lu : écriture manuscrite, "
        "caractères trop petits, flou, contre-jour",
        "Visages, plaques d'immatriculation, signatures manuscrites",
        "Texte dans une écriture non latine",
        "Codes-barres et QR codes",
        "Mise en page en colonnes : le texte est lu ligne à ligne, ce qui peut "
        "entrelacer deux colonnes et gêner la reconnaissance des noms",
    ],
}
