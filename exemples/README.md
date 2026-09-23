# Jeu de démonstration

Six fichiers à **données entièrement fictives**, destinés à essayer
l'application sans risquer de vraies données. Aucune personne, société, adresse,
coordonnée bancaire ni numéro de sécurité sociale réels n'y figure.

Ce document décrit ce que contient chaque fichier et ce qu'il permet de
vérifier. Les décomptes correspondent au **mode dégradé** — modèle GLiNER
absent, règles déterministes seules — et comptent des **valeurs distinctes**,
pas des occurrences. Avec le modèle installé s'y ajoutent les noms de personnes,
les organisations et les adresses reconnus par le modèle.

---

## Conventions communes

Les trois fichiers les plus récents partagent un même univers fictif : une même
donnée se suit d'un fichier à l'autre.

| Rôle | Valeur |
|------|--------|
| Société | Ateliers Tanguy EURL, 14 rue des Charmilles, 44000 Nantes |
| SIREN / SIRET siège | `404833048` / `40483304800022` |
| Gérante | Delphine Salvatore |
| Salarié | Damien Lacroix, 8 impasse des Lilas, 44300 Nantes, né le 12/03/1984 |
| NIR du salarié | `1 84 03 44 109 025 32` |
| Compte de la société | `FR76 3000 4028 3700 0123 4567 873` (BIC `BNPAFRPPXXX`) |
| Compte du salarié | `FR76 1680 6050 1400 0918 2736 413` (BIC `AGRIFRPP883`) |
| Prestataire | Cabinet Marchand & Associés, SIRET `51032719000037`, Pierre Marchand |
| Client | Bureau Sablons SA, SIRET `79214860300014` |

**Toutes les clés de contrôle sont valides** : Luhn pour les SIREN et SIRET,
clé de sécurité sociale pour les NIR, modulo 97 pour les IBAN. C'est
indispensable : les règles rejettent un SIREN ou un SIRET à clé fausse, et
marquent « non confirmé » un IBAN ou un NIR au format plausible mais à clé
invalide.

---

## `clients_demo.csv`

Fichier client tabulaire — **120 lignes + en-tête, 19 colonnes**, séparateur `;`,
UTF-8 avec BOM.

- Colonnes d'identité : `raison_sociale`, `contact_prenom`, `contact_nom`,
  `email`, `telephone`, `ville`, `code_postal`, `commercial`
- Nomenclatures répétitives : `categorie` (`STAT_PME`, `STAT_GRAND_COMPTE`…),
  `secteur`, `statut`
- Mesures numériques : `effectif`, `ca_2023`, `ca_2024`, `ca_2025`,
  `taux_marge_pct`
- Dates : `date_entree`, `derniere_commande`

**À vérifier**

- Le séparateur `;` et l'encodage sont détectés seuls, et restitués tels quels
  dans le fichier de sortie.
- Le plan de colonnes type les identités et **écarte** les mesures (`ca_2025`)
  et les nomenclatures (`statut`) : masquer un chiffre d'affaires rendrait le
  fichier inexploitable.
- Le forçage manuel d'une colonne, par clic sur son en-tête, masque les
  120 cellules — essayer sur `secteur`. L'opération inverse libère une colonne
  typée — essayer sur `email`.
- La ligne d'en-tête reste intacte après masquage.

## `clients_demo.xlsx`

Le même jeu converti en classeur : une feuille `Clients`, 121 lignes ×
19 colonnes.

**À vérifier**

- Revue feuille par feuille, mêmes décisions de colonnes que le CSV.
- Édition en place : styles, formats et formules survivent au masquage.
- `ca_2025` reste un **nombre** dans le fichier de sortie, pas le texte `[CA]`.

## `compte_rendu_reunion_demo.pdf`

Compte rendu de réunion — **1 page, ~2 800 caractères**, PDF natif (texte
sélectionnable, pas une image).

- Métadonnées d'identité : auteur « S. Delaunay - Novalis Industries SAS »,
  titre, sujet, mots-clés, créateur
- **11 valeurs confirmées** : 3 téléphones, 2 adresses, 2 codes postaux,
  2 mots de passe, 1 e-mail, 1 identifiant

**À vérifier**

- Le caviardage **détruit réellement** le texte : rouvrir le PDF de sortie,
  sélectionner la zone noircie, vérifier qu'il n'y a plus rien à copier.
- L'export en `.txt` donne le même contenu, masqué.
- Trois valeurs remontent en **« non confirmé »**, et c'est voulu : deux NIR —
  dont un coupé par un retour à la ligne — et un IBAN à clé fausse. Format
  plausible, clé invalide : l'application les signale sans les masquer d'office.

## `Contrat_prestation_Ateliers_Tanguy_EURL.docx`

Contrat de prestation de services — 6 articles, 25 paragraphes, 2 tableaux.
**Le nom du fichier porte lui-même la raison sociale.**

- **En-tête** : raison sociale, adresse, téléphone, e-mail de contact
- **Pied de page** : SIRET, RCS, n° de TVA, lien hypertexte, numéro de page
  automatique (champ `PAGE`)
- **3 liens hypertexte réels** — relations externes OOXML, pas du texte brut :
  un dans le pied de page, deux dans le corps
- Tableau de 5 interlocuteurs : nom, fonction, e-mail, téléphone direct
- IBAN et BIC des deux parties, identifiant et mot de passe provisoire, NIR et
  date de naissance d'un salarié
- **Métadonnées identifiantes** : auteur « Delphine Salvatore », dernier
  modificateur « Sandra Leclerc », titre, sujet, catégorie, mots-clés,
  commentaires

**À vérifier**

- **35 valeurs distinctes**, toutes confirmées : 7 e-mails, 7 métadonnées
  (type `META`), 6 téléphones, 3 adresses, 3 codes postaux, 2 SIRET, 2 IBAN,
  1 SIREN, 1 NIR, 1 date de naissance, 1 identifiant, 1 mot de passe.
- Le masquage atteint l'**en-tête et le pied de page**, pas seulement le corps.
- La mise en forme survit : gras, couleurs, tableaux, bordures, numéro de page.
- Les liens hypertexte restent cliquables. Les URL ne sont **pas** masquées par
  défaut, le type `URL` étant inactif ; l'activer dans les Paramètres doit faire
  apparaître les deux liens du corps.
- Les métadonnées d'identité sont purgées du fichier de sortie.

## `Bulletin_de_paie_2025-06_LACROIX_Damien.pdf`

Bulletin de paie de juin 2025 — **1 page, ~3 600 caractères**, PDF natif, mise
en page dense en tableaux.

- Bloc employeur : raison sociale, adresse, SIRET, code APE, n° URSSAF,
  convention collective, téléphone, e-mail
- Bloc salarié : identité, adresse, NIR, date et lieu de naissance, matricule,
  emploi, classification, date d'entrée
- Tableau de paie : 4 éléments de rémunération, 13 lignes de cotisations, bases,
  taux salariaux et patronaux
- Nets, cumuls, prélèvement à la source, coût employeur
- Bloc paiement : IBAN de l'employeur **et** du salarié, BIC, solde de congés,
  contact du service paie, URL du portail RH
- Bloc observations : acompte, rattachement d'un conjoint à la mutuelle avec sa
  date de naissance, visite médicale avec nom et adresse du médecin, entretien
  professionnel
- Métadonnées : auteur « Sandra Leclerc », titre, sujet, mots-clés

**À vérifier**

- **18 valeurs distinctes**, toutes confirmées : 3 adresses, 3 e-mails,
  3 téléphones, 2 dates de naissance, 2 IBAN, 2 codes postaux, 1 NIR, 1 SIREN,
  1 SIRET. Aucune valeur « non confirmée ».
- Le NIR et les deux IBAN sont reconnus malgré leur découpage en groupes de
  chiffres séparés par des espaces.
- Le caviardage tient sur une mise en page en colonnes : montants et taux
  restent lisibles, seules les données personnelles disparaissent.
- Les chiffres sont cohérents et doivent le rester : brut 2 755,98 € → net payé
  2 046,50 €, coût employeur 3 735,45 €.

## `404833048FEC20251231.txt`

Fichier des écritures comptables (FEC) d'un exercice complet.

- **Nom normalisé** `<Siren>FEC<AAAAMMJJ de clôture>.txt`, conformément à
  l'article A. 47 A-1 du LPF — donc le **SIREN** (9 chiffres), pas le SIRET.
  Les SIRET, eux, figurent dans les libellés d'écriture.
- **372 lignes d'écriture + 1 ligne d'en-tête**, 18 colonnes séparées par des
  tabulations, UTF-8, fins de ligne CRLF
- Exercice 2025 complet, **126 écritures**, 6 journaux : ventes (108 lignes),
  achats (108), paie (72), banque (48), caisse (24), opérations diverses (12)
- **Débit et crédit s'équilibrent exactement** : 539 144,91 € de part et d'autre
- **39 comptes, dont des comptes nominatifs** :
  `421LACR LACROIX Damien - rémunérations dues`,
  `455SALV SALVATORE Delphine - compte courant d'associé`, `401PREV`,
  `411BERG`, `425SALV`… Les comptes auxiliaires (`CompAuxLib`) portent eux aussi
  des noms de personnes et de sociétés.
- **Libellés d'écriture porteurs de données personnelles** : IBAN de virement de
  salaire, NIR, téléphones, e-mails, adresses postales, SIRET, URL, date de
  naissance d'un stagiaire, numéro de permis de conduire
- Lettrage et dates de lettrage sur une partie des ventes, quelques lignes en
  devise

**À vérifier**

- Le fichier s'ouvre sans erreur malgré ses 78 Ko et ses 373 lignes.
- Les valeurs légitimes sont toutes masquées : **7 téléphones, 6 e-mails,
  4 adresses, 3 SIRET, 3 codes postaux, 2 IBAN, 1 NIR, 1 date de naissance**.
- L'encodage UTF-8, les tabulations et les fins de ligne CRLF sont restitués à
  l'identique : le fichier de sortie doit rester un FEC valide, relisible par un
  tableur ou un outil de contrôle.
- Les montants, les numéros de compte et les dates ne sont **pas** touchés.
- L'équilibre débit/crédit est intact après masquage.
- Ce fichier fait aussi remonter du bruit de détection — voir ci-dessous.

---

## Points connus (état observé en v0.8.1)

Le FEC, lu comme un `.txt`, est le seul fichier du jeu qui aligne des colonnes
de chiffres séparées par des tabulations. Il fait apparaître quatre débordements
de règles, absents des autres fichiers. Sur les **57 valeurs confirmées**, 27
sont légitimes et **30 sont du bruit** :

| Règle | Bruit | Origine |
|-------|-------|---------|
| Téléphone | 21 valeurs | la fin d'une date `JJ/MM/AAAA` collée, par la tabulation, au début de la date `AAAAMMJJ` de la colonne suivante (`03` + tabulation + `20250328`) |
| Téléphone | 1 valeur | `0219840312`, fragment du numéro de permis de conduire `440219840312` |
| Code postal | 5 valeurs | des montants à 5 chiffres avant la virgule (`12500,00` → `12500`) |
| Identifiant | 3 valeurs | l'URL `…/login` suivie d'une tabulation puis du montant, que la règle contextuelle prend pour l'identifiant |

À quoi s'ajoutent **environ 530 IBAN « non confirmés »** : les références de
pièce et les numéros d'écriture (`AC00001`, `FA20250001`…) suivis d'une
tabulation ont le format d'un IBAN. Leur clé modulo 97 étant invalide, ils
restent non confirmés et, sur le chemin `.txt`, les valeurs non confirmées ne
sont pas masquées : le fichier de sortie n'en porte pas trace.

Trois de ces quatre débordements ont la même cause — une tabulation acceptée
comme séparateur interne à la valeur.
