# Anonymator

Application locale Windows d'anonymisation de texte et de fichiers comptables.

Détecte et remplace les données personnelles (noms, emails, IBAN, numéros de téléphone…) par des étiquettes de catégorie (`[PERSONNE]`, `[EMAIL]`…). **Aucune donnée ne quitte votre machine.**

> **Nom du produit.** *Anonymator* est le nom du **projet**. L'application est diffusée en
> plusieurs **éditions**, chacune avec son propre nom de produit, son thème de couleurs, son
> archive et son exécutable — pour un fonctionnement strictement identique. Ce document parle
> donc du projet et de « l'application ».

---

## Installation

1. Télécharger et dézipper l'archive `.zip` de votre édition.
2. Lancer le fichier `.exe` situé **à la racine** du dossier dézippé — c'est le seul, et il
   porte le nom de votre édition.
3. Au **premier lancement**, l'application propose de télécharger le modèle de détection
   GLiNER (~2,2 Go). Une connexion Internet est nécessaire pour cette seule étape ; les
   lancements suivants fonctionnent hors-ligne.
   Sans le modèle, l'application démarre quand même en **mode dégradé** : les détections par
   règles (e-mail, téléphone, IBAN, SIREN/SIRET, NIR, mots de passe…) restent opérationnelles,
   seuls les noms, adresses et organisations sont hors de portée. Le téléchargement peut être
   relancé plus tard depuis l'accueil ou les Paramètres, sans redémarrer.

Le dossier dézippé contient aussi `exemples/` (jeu de fichiers de démonstration à données
fictives), `LICENSE` et `_internal/` (composants techniques — ne rien y modifier).

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
2. Cliquer **Ouvrir…** → sélectionner un `.txt`, `.csv`, `.xlsx`, `.docx` ou `.pptx`.
3. Aperçu du fichier dans le tableau.
4. Cliquer **Anonymiser et enregistrer** → le fichier anonymisé est sauvegardé dans le dossier de sortie.
5. L'original n'est **jamais modifié**.

### Paramètres

- **Thème** : verrouillé aux couleurs de votre édition (le sélecteur n'apparaît que sur la
  build de développement).
- **Dossier de sortie** : dossier cible pour les fichiers anonymisés. Laissé vide, le fichier
  est écrit à côté de son original.
- **Types d'entités à détecter** : activation catégorie par catégorie (le BIC est inactif par
  défaut).
- **Modèle de détection intelligente** : état d'installation, téléchargement et réparation.

---

## Formats supportés

| Format | Support |
|--------|---------|
| `.txt` | ✅ Texte intégral |
| `.csv` | ✅ Par colonnes (séparateur auto-détecté, encodage préservé) |
| `.xlsx` | ✅ Édition en place (styles, formules et onglets conservés), revue feuille par feuille |
| `.docx` / `.pptx` | ✅ Contenu Word/PowerPoint, mise en forme conservée, purge des métadonnées d'identité |
| `.pdf` | ✅ PDF natifs : caviardage (destruction réelle) ou extraction .txt. Scannés (image seule) non supportés. |

---

## Données & confidentialité

- Traitement **100 % local** : aucun appel réseau en usage normal.
- Le téléchargement initial du modèle GLiNER est le seul accès réseau (une seule fois).
- Au premier lancement, l'application **propose** de s'enregistrer (facultatif, jamais bloquant ;
  une relance au 5ᵉ lancement au plus). « M'enregistrer » ouvre un formulaire dans votre
  navigateur : l'application elle-même n'envoie rien. Le choix est mémorisé dans
  `%USERPROFILE%\.anonymator\preferences.json`.
- Le modèle est mis en cache dans `%USERPROFILE%\.cache\huggingface`.
- Le rapport d'audit (optionnel) contient les valeurs remplacées — à stocker et partager avec précaution.

---

## Problèmes connus

| Symptôme | Solution |
|----------|----------|
| Téléchargement très lent au 1er lancement | Connexion Internet requise (~2,2 Go) ; patienter |
| Échec du téléchargement : `CERTIFICATE_VERIFY_FAILED` | Antivirus inspectant le HTTPS (Norton, Kaspersky…). L'app valide via le magasin de certificats Windows depuis la v0.4.3 ; sinon, ajouter une exception pour l'exécutable |
| Fichier CSV mal parsé | Vérifier encodage (Latin-1/UTF-8) et séparateur |
| `.pdf` scanné (image seule) | OCR non supporté en v1 — message clair, aucun plantage |
| Nom manqué lors de la détection | Vérifier que le modèle GLiNER est installé ; sur un tableau, forcer la colonne via un clic sur son en-tête ; sinon créer une règle « Toujours masquer » |

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
