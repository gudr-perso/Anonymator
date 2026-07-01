# Anonymator

Application locale Windows d'anonymisation de texte et de fichiers comptables.

Détecte et remplace les données personnelles (noms, emails, IBAN, numéros de téléphone…) par des étiquettes de catégorie (`[PERSONNE]`, `[EMAIL]`…). **Aucune donnée ne quitte votre machine.**

---

## Installation

1. Télécharger et dézipper `Anonymator-vX.X.zip`.
2. Lancer `anonymator.exe` dans le dossier dézippé.
3. Au **premier lancement**, l'application télécharge le modèle de détection GLiNER (~300 Mo).
   Une connexion Internet est nécessaire pour cette étape initiale uniquement.
   Les lancements suivants fonctionnent hors-ligne.

---

## Utilisation

### Mode Texte

1. Cliquer **Texte** sur l'écran d'accueil.
2. Coller ou saisir du texte dans la zone de saisie.
3. Cliquer **Analyser** → les entités détectées apparaissent surlignées (couleur par type) et listées.
4. Décocher les entités à **ne pas** masquer.
5. Cliquer **Appliquer le masquage** → le texte anonymisé s'affiche.
6. **Copier** ou **Exporter .txt**.

### Mode Fichier

1. Cliquer **Fichier** sur l'écran d'accueil.
2. Cliquer **Ouvrir…** → sélectionner un `.txt`, `.csv` ou `.xlsx`.
3. Aperçu du fichier dans le tableau.
4. Cliquer **Anonymiser et enregistrer** → le fichier anonymisé est sauvegardé dans le dossier de sortie.
5. L'original n'est **jamais modifié**.

### Paramètres

- **Thème** : France Cuma Numérique (vert) ou CAP Consulting (bleu).
- **Dossier de sortie** : dossier cible pour les fichiers anonymisés.

---

## Formats supportés

| Format | Support |
|--------|---------|
| `.txt` | ✅ Texte intégral |
| `.csv` | ✅ Par colonnes (séparateur auto-détecté, encodage préservé) |
| `.xlsx` | ✅ Édition en place (styles, formules et onglets conservés) |
| `.pdf` | ✅ PDF natifs : caviardage (destruction réelle) ou extraction .txt. Scannés (image seule) non supportés. |

---

## Données & confidentialité

- Traitement **100 % local** : aucun appel réseau en usage normal.
- Le téléchargement initial du modèle GLiNER est le seul accès réseau (une seule fois).
- Le modèle est mis en cache dans `%USERPROFILE%\.cache\huggingface`.
- Le rapport d'audit (optionnel) contient les valeurs remplacées — à stocker et partager avec précaution.

---

## Problèmes connus

| Symptôme | Solution |
|----------|----------|
| Téléchargement très lent au 1er lancement | Connexion Internet requise (~300 Mo) ; patienter |
| Fichier CSV mal parsé | Vérifier encodage (Latin-1/UTF-8) et séparateur |
| `.pdf` scanné (image seule) | OCR non supporté en v1 — message clair, aucun plantage |
| Nom manqué lors de la détection | Ajouter manuellement via la sélection de texte (mode Texte) |

---

## Licence

Anonymator est distribué sous licence **AGPL-3.0** — voir [LICENSE](LICENSE).

Le code source complet est disponible sur
<https://github.com/gudr-perso/Anonymator>. Chaque version distribuée correspond à
un tag `vX.Y.Z` du dépôt : le binaire livré correspond exactement au source publié
sous ce tag (AGPL art. 6).

Attributions :

- Embarque **PyMuPDF** © Artifex Software — AGPL-3.0.
- Embarque **GLiNER** — modèle `urchade/gliner_multi-v2.1`, Apache-2.0 (usage commercial autorisé).
- Interface **Qt/PySide6** sous LGPL-3.0 et autres composants tiers : voir
  [`third-party-licenses/`](third-party-licenses/README.md) (inclus dans le zip distribué).
