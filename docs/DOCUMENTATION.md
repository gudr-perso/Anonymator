# Documentation Anonymator

> Version du document : 1.0 — correspond à Anonymator **v0.3.0**
> Licence : AGPL-3.0-or-later · Code source : <https://github.com/gudr-perso/Anonymator>

Anonymator est une application **Windows 100 % locale** qui détecte et masque les
données personnelles et sensibles (noms, adresses, e-mails, IBAN, numéros de
sécurité sociale, mots de passe…) dans du texte et des fichiers bureautiques,
**sans qu'aucune donnée ne quitte le poste de travail**.

Cette documentation est organisée en trois parties :

1. [Documentation technique](#1-documentation-technique) — stack, modèles, méthodes de détection, licences.
2. [Documentation fonctionnelle](#2-documentation-fonctionnelle) — installation et prise en main, écran par écran.
3. [Argumentaire commercial](#3-argumentaire-commercial) — pourquoi anonymiser, ce que l'outil apporte.

---

## 1. Documentation technique

### 1.1 Vue d'ensemble

Anonymator est un logiciel de bureau autonome. Il fonctionne **hors ligne** après
une unique phase d'initialisation (téléchargement du modèle d'intelligence
artificielle). Le traitement — détection comme masquage — s'effectue intégralement
sur la machine de l'utilisateur : aucun appel réseau n'est émis en usage normal.

### 1.2 Stack technique

| Couche | Technologie | Rôle |
|--------|-------------|------|
| Langage | **Python ≥ 3.11** | Cœur applicatif |
| Interface graphique | **PySide6 (Qt 6)** | Fenêtre, écrans, thèmes |
| Détection IA (NER) | **GLiNER** — modèle `urchade/gliner_multi-v2.1` | Noms, adresses, organisations |
| Moteur IA sous-jacent | **PyTorch / Hugging Face Transformers** | Exécution du modèle GLiNER |
| PDF | **PyMuPDF** (© Artifex) | Lecture, caviardage réel, extraction |
| Tableur | **openpyxl** | Lecture/écriture `.xlsx` (styles, formules, onglets préservés) |
| Bureautique Office | **python-docx**, **python-pptx** | Traitement `.docx` et `.pptx` (OOXML) |
| Packaging | **PyInstaller** (`anonymator.spec`) | Génération de l'exécutable Windows autonome |
| Tests | **pytest**, **pytest-qt** | Suite de tests unitaires et d'intégration |

L'application est distribuée sous forme d'un **exécutable Windows autonome**
(`anonymator.exe`), produit par PyInstaller à partir du fichier de spécification
`anonymator.spec`. Aucune installation de Python n'est requise sur le poste cible.

**Distribution du modèle IA.** Le modèle GLiNER (~300 Mo) n'est **pas** embarqué
dans l'exécutable. Il est téléchargé au premier lancement depuis Hugging Face et
mis en cache localement dans `%USERPROFILE%\.cache\huggingface`. Les lancements
suivants s'effectuent hors ligne.

### 1.3 Qu'est-ce que le NER ?

Le **NER** (*Named Entity Recognition*, ou « reconnaissance d'entités nommées »)
est une tâche de traitement automatique du langage naturel (TALN) qui consiste à
**repérer, dans un texte libre, les portions qui désignent une entité du monde
réel** et à leur attribuer une catégorie : une personne, un lieu, une
organisation, une date, etc.

Là où une expression régulière ne sait reconnaître qu'un **format** (une suite de
chiffres, un motif d'e-mail…), le NER s'appuie sur le **contexte** et le **sens**
de la phrase. Il sait par exemple que dans « *J'ai rencontré Martin Boulanger* »,
« Martin Boulanger » est une personne, tandis que dans « *la boulangerie Martin* »,
« Martin » qualifie un commerce. Cette capacité est indispensable pour détecter
les noms de personnes, les adresses postales rédigées en prose ou les raisons
sociales — des données qui n'ont **aucun format fixe** et qu'aucune règle ne peut
capturer de façon fiable.

### 1.4 Qu'est-ce que GLiNER ?

**GLiNER** (*Generalist and Lightweight model for Named Entity Recognition*) est un
modèle de reconnaissance d'entités nommées **open source**, reconnu comme l'une
des références du domaine. Il a été conçu et publié par une équipe de recherche
**française** (travaux d'Urchade Zaratiana et de ses co-auteurs, menés en France),
ce qui en fait une **fierté de la recherche française en IA** dans un domaine
largement dominé par les grands acteurs anglophones.

**Comment il fonctionne.** Contrairement aux modèles de NER classiques, entraînés
sur une liste **figée** de catégories (personne, lieu, organisation…), GLiNER est
un modèle **« zero-shot »** : on lui fournit, au moment de l'analyse, la **liste
des types d'entités recherchés en langage naturel** (par exemple « personne »,
« adresse postale », « organisation »). Le modèle compare alors chaque portion du
texte à ces libellés et renvoie les correspondances avec un **score de
confiance**. Cette souplesse permet d'ajuster ce que l'on cherche sans
réentraîner le modèle.

Techniquement, GLiNER repose sur un **transformeur bidirectionnel** (de la famille
BERT) qui encode simultanément le texte et les libellés de types, puis mesure leur
adéquation. Il est **léger** — il tourne sur un simple CPU, sans carte graphique —
tout en restant compétitif face à des modèles bien plus lourds. C'est cette
combinaison **précision / légèreté / exécution locale** qui le rend idéal pour un
outil de bureau confidentiel comme Anonymator.

Dans Anonymator, le modèle utilisé est `urchade/gliner_multi-v2.1`, une variante
**multilingue** (dont le français), publiée sous licence **Apache-2.0** (usage
commercial autorisé).

> **Note d'implémentation — le *chunking*.** GLiNER tronque silencieusement toute
> entrée dépassant ~384 tokens (environ 1 500 caractères de français dense) :
> au-delà, le bas du texte n'est jamais analysé. Anonymator découpe donc les longs
> textes en segments < 1 000 caractères (module `core/chunking.py`), en coupant sur
> les espaces, puis rebase les positions des entités détectées. Seul le NER est
> découpé : la détection déterministe voit toujours le texte entier (un IBAN coupé
> en deux ne serait plus reconnu).

### 1.5 Les deux méthodes de détection

Anonymator combine **deux approches complémentaires**, dont les résultats sont
ensuite fusionnés.

**a) Détection déterministe (par règles).** Pour toutes les données ayant un
**format normé**, l'application utilise des expressions régulières **doublées d'une
validation par clé de contrôle**, ce qui élimine la quasi-totalité des faux
positifs :

| Donnée | Détection | Validation |
|--------|-----------|------------|
| E-mail | motif `local@domaine` | — |
| Téléphone (FR) | formats `0X…`, `+33…` | — |
| IBAN | motif ISO 13616 | **clé modulo 97** |
| BIC / SWIFT | motif 8 ou 11 caractères | **code pays ISO 3166** |
| SIREN | 9 chiffres | **clé de Luhn** |
| SIRET | 14 chiffres | **clé de Luhn** |
| N° de sécurité sociale (NIR) | motif INSEE | **clé de contrôle modulo 97** |
| Code postal (FR) | 5 chiffres | département plausible (01–98) |
| Adresse postale | numéro + type de voie + nom | — |
| URL | `http(s)://…` | — |

Lorsqu'une valeur a le **bon format mais une clé de contrôle invalide** (IBAN, NIR),
elle n'est pas rejetée : elle est signalée comme **« détectée mais non conforme »**
et proposée à l'utilisateur, décochée par défaut, pour arbitrage manuel.

**b) Détection intelligente (NER via GLiNER).** Pour les données **sans format
fixe** — noms de personnes, adresses en prose, organisations — Anonymator sollicite
le modèle GLiNER décrit ci-dessus.

**c) Détecteurs contextuels et par entropie (secrets).** Un module dédié
(`secrets_detect.py`) repère les **identifiants et mots de passe** de deux façons :
par **mots-clés contextuels** (« mot de passe : … », « login … ») et par **analyse
d'entropie** (un jeton mêlant minuscules, majuscules et chiffres est traité comme
un secret probable).

**d) Règles métier de l'utilisateur.** L'utilisateur peut ajouter ses propres
règles « **toujours masquer** » ou « **ne jamais masquer** » (voir §2.6).

**Fusion et priorité.** Toutes les détections passent par un moteur de fusion
(`merge.py`) qui **élimine les chevauchements** selon un ordre de priorité :
détection déterministe / règle métier d'abord, puis score de confiance, puis
longueur du segment. Le remplacement final substitue à chaque valeur retenue
l'**étiquette de sa catégorie** (`[PERSONNE]`, `[EMAIL]`, `[IBAN]`…), de la fin du
texte vers le début pour préserver les positions.

### 1.6 Référentiel des entités et niveau de risque

Les types d'entités sont déclarés dans un référentiel (`config/entities.json`).
Chaque type porte une **méthode** de détection, une **étiquette** de remplacement,
un état **actif/inactif** par défaut et une **sensibilité** (Haute / Moyenne /
Basse).

| Code | Libellé | Méthode | Étiquette | Sensibilité |
|------|---------|---------|-----------|-------------|
| PERSON | Personne | NER | `[PERSONNE]` | Haute |
| ADDRESS | Adresse | NER | `[ADRESSE]` | Haute |
| ORG | Organisation | NER | `[ORG]` | Moyenne |
| EMAIL | E-mail | déterministe | `[EMAIL]` | Haute |
| PHONE | Téléphone | déterministe | `[TEL]` | Haute |
| IBAN | IBAN | déterministe | `[IBAN]` | Haute |
| BIC | BIC / SWIFT | déterministe | `[BIC]` | Moyenne |
| SIREN | SIREN | déterministe | `[SIREN]` | Moyenne |
| SIRET | SIRET | déterministe | `[SIRET]` | Moyenne |
| NIR | N° sécu | déterministe | `[NIR]` | Haute |
| POSTAL_CODE | Code postal | déterministe | `[CP]` | Basse |
| URL | URL | déterministe | `[URL]` | Basse |
| LOGIN | Identifiant | contextuel | `[LOGIN]` | Haute |
| PASSWORD | Mot de passe | contextuel | `[SECRET]` | Haute |
| REGLE_INTERNE | Règle interne | règle | `[REGLE-INTERNE]` | Moyenne |

La **sensibilité la plus élevée** parmi les entités retenues détermine un **niveau
de risque global** affiché à l'utilisateur (Élevé / Moyen / Faible), pour guider la
décision de partage.

### 1.7 Traçabilité — le rapport d'audit

À chaque anonymisation, Anonymator peut produire un **rapport d'audit** (module
`report/audit.py`), exportable en **CSV** ou **JSON**, qui recense pour chaque
valeur remplacée : le type, la valeur originale, l'étiquette appliquée, le nombre
d'occurrences, les emplacements et le statut « confirmé ou non ».

> ⚠️ Ce rapport contient les **valeurs d'origine en clair**. Il constitue une pièce
> sensible : à stocker et partager avec les mêmes précautions que la donnée source.

### 1.8 Formats de fichiers pris en charge

| Format | Traitement |
|--------|-----------|
| `.txt` | Texte intégral |
| `.csv` | Par colonnes, séparateur auto-détecté, encodage préservé |
| `.xlsx` | Édition en place — styles, formules et onglets conservés |
| `.docx` | Traitement du contenu OOXML (Word) |
| `.pptx` | Traitement du contenu OOXML (PowerPoint) |
| `.pdf` (natif) | **Caviardage réel** (destruction du texte sous le rectangle noir) **ou** extraction `.txt` |
| `.pdf` (scanné, image seule) | Non supporté — message explicite, aucun plantage (pas d'OCR en v1) |

Le fichier **original n'est jamais modifié** : les sorties sont écrites dans le
dossier de sortie configuré.

### 1.9 Licences et modèle de distribution

Anonymator est un **logiciel libre** distribué sous licence **AGPL-3.0-or-later**.
Chaque version publiée correspond à un tag `vX.Y.Z` du dépôt public : le binaire
livré correspond exactement au source publié sous ce tag (AGPL, art. 6).

| Composant | Éditeur / origine | Licence | Portée |
|-----------|-------------------|---------|--------|
| **Anonymator** | gudr-perso | **AGPL-3.0** | Application |
| **PyMuPDF** | © Artifex Software | **AGPL-3.0** | Traitement PDF |
| **GLiNER** (`gliner_multi-v2.1`) | Urchade Zaratiana et al. (France) | **Apache-2.0** | Modèle NER — **usage commercial autorisé** |
| **Qt / PySide6** | The Qt Company | **LGPL-3.0** | Interface graphique |

Le détail complet des composants tiers est fourni dans `third-party-licenses/`,
inclus dans l'archive distribuée.

> **Modèle économique.** Le choix de l'AGPL (dépôt public) est cohérent avec une
> monétisation par la **prestation de service** (déploiement, adaptation,
> accompagnement, règles métier sur mesure) plutôt que par la vente de licences.

---

## 2. Documentation fonctionnelle

*Destinée à un nouvel utilisateur.*

### 2.1 Installation

Anonymator ne nécessite **aucun droit administrateur** ni installation système.

1. **Télécharger** l'archive `Anonymator-vX.X.zip`.
2. **Dézipper** l'archive dans un dossier de votre choix.
3. **Lancer** `anonymator.exe` dans le dossier dézippé.
4. Au **premier lancement uniquement**, l'application propose de télécharger le
   modèle de détection intelligente **GLiNER (~300 Mo)**. Une **connexion
   Internet** est nécessaire pour cette seule étape.
   - Vous pouvez cliquer **« Télécharger maintenant »** pour l'activer tout de suite,
     ou **« Plus tard »** pour commencer sans lui.
   - **Sans le modèle**, l'application fonctionne déjà : toutes les détections **par
     règles** (e-mail, téléphone, IBAN, SIREN/SIRET, NIR, mots de passe…) sont
     opérationnelles. Seule la détection des **noms, adresses et organisations**
     reste indisponible tant que le modèle n'est pas installé (« mode dégradé »).
5. Les lancements suivants s'effectuent **entièrement hors ligne**.

### 2.2 L'écran d'accueil

L'écran d'accueil présente le pitch de l'outil et un menu **« Par où commencer ? »**
donnant accès aux six écrans de l'application :

- **Coller du texte** — analyser et masquer un texte collé.
- **Importer un fichier** — `.txt`, `.csv`, `.xlsx`, `.docx` ou `.pptx`.
- **Importer un PDF** — caviarder ou extraire (PDF natifs).
- **Paramètres** — thème, dossier de sortie, types détectés, modèle IA.
- **Gestion des règles** — règles métier personnalisées.
- **À propos** — licence, version et mentions.

Si le modèle IA n'est pas encore installé, un encart **« Activer la détection
intelligente »** apparaît en haut, avec les boutons *Télécharger maintenant* /
*Plus tard*.

### 2.3 Menu « Texte »

Pour anonymiser un texte collé (e-mail, note, extrait de document…) :

1. **Coller ou saisir** votre texte dans la zone de saisie.
2. Cliquer **« Analyser »**. Les entités détectées apparaissent **surlignées**
   (une couleur par type) dans le texte et **listées** à côté.
3. **Revoir la sélection** :
   - Chaque entité détectée est **cochée par défaut** (elle sera masquée).
   - **Décochez** celles que vous souhaitez conserver.
   - Les entités **« détectées mais non conformes »** (bon format, clé de contrôle
     invalide) sont signalées distinctement et **décochées par défaut** — cochez-les
     pour les masquer si nécessaire.
   - Vous pouvez **ajouter une entité manuellement** en sélectionnant une portion de
     texte que la détection aurait manquée.
4. Un **niveau de risque** (Élevé / Moyen / Faible) synthétise la sensibilité de ce
   qui a été détecté.
5. Cliquer **« Appliquer le masquage »** : le texte anonymisé s'affiche, chaque
   valeur remplacée par son étiquette (`[PERSONNE]`, `[EMAIL]`…).
6. **Copier** le résultat ou l'**exporter en `.txt`**.

### 2.4 Menu « Fichier »

Pour anonymiser un fichier bureautique :

1. Cliquer **« Ouvrir… »** et sélectionner un `.txt`, `.csv`, `.xlsx`, `.docx` ou
   `.pptx`.
2. Le contenu s'affiche en **aperçu**.
3. Cliquer **« Analyser »** : les entités détectées sont présentées pour revue,
   comme en mode Texte (cases à cocher, entités non conformes signalées).
4. Cliquer **« Anonymiser et enregistrer »** : le fichier anonymisé est écrit dans
   le **dossier de sortie**. Pour les `.xlsx`, les **styles, formules et onglets**
   sont conservés ; pour les `.csv`, l'**encodage et le séparateur** sont préservés.
5. **L'original n'est jamais modifié.**

### 2.5 Menu « PDF »

Deux traitements sont proposés pour les **PDF natifs** (texte sélectionnable) :

- **Caviardage** — les zones détectées sont recouvertes d'un rectangle et le texte
  situé dessous est **réellement supprimé** du fichier (pas seulement masqué
  visuellement). Le PDF reste un PDF.
- **Extraction `.txt`** — le texte du PDF est extrait puis anonymisé comme en mode
  Texte.

Fonctionnement :

1. **« Ouvrir »** un fichier `.pdf`.
2. **« Analyser »** : les entités détectées sont surlignées page par page sur
   l'aperçu du document.
3. Revoir la sélection (cases à cocher). Vous pouvez tracer une **« Zone manuelle »**
   pour caviarder une région que la détection n'aurait pas repérée.
4. Enregistrer le PDF caviardé (ou exporter le texte).

> Les **PDF scannés** (image seule, sans couche texte) ne sont pas pris en charge
> en v1 : l'application l'indique clairement, sans planter.

### 2.6 Menu « Gestion des règles »

Cet écran permet de définir vos **règles métier**, utiles pour adapter l'outil à vos
conventions internes :

- **« Ne jamais masquer »** — protège une codification interne que la détection
  pourrait confondre avec une donnée personnelle (ex. une référence article
  `A#######` = *A* suivi de 7 chiffres, ou une convention `FACT.*`).
- **« Toujours masquer »** — force le remplacement de tout ce qui correspond au
  motif, par l'étiquette `[REGLE-INTERNE]`.

Deux modes d'écriture des motifs :

- **Mode simple** — `#` = un chiffre, `?` = un caractère, `*` = n'importe quelle
  suite. Exemple : `A#######`.
- **Mode expert** — expression régulière complète.

Les règles sont **enregistrées** sur le poste (`~/.anonymator/user_rules.json`) et
appliquées à toutes les analyses. Un bouton permet d'**ouvrir le dossier** contenant
le fichier de règles.

### 2.7 Menu « Paramètres »

Trois blocs de réglages :

- **Général**
  - **Thème** de l'application : *France Cuma Numérique* (vert) ou *CAP Consulting*
    (bleu).
  - **Dossier de sortie** : dossier cible où sont écrits les fichiers anonymisés.
- **Types d'entités à détecter** — activez / désactivez chaque catégorie (Personne,
  Adresse, E-mail, IBAN…). Un compteur indique le nombre de types actifs. Certaines
  catégories peu sensibles (BIC, code postal, URL) sont **désactivées par défaut**.
- **Modèle de détection intelligente** — état d'installation du modèle GLiNER, taille
  et emplacement du cache, bouton pour le **télécharger** ou le **réparer**
  (re-télécharger), avec barre de progression.

### 2.8 Menu « À propos »

Rappelle la **version** de l'application, la **licence AGPL-3.0** avec un lien vers
le **code source sur GitHub** (tag correspondant à la version), et la liste des
**composants embarqués** avec leur licence (PyMuPDF, GLiNER).

### 2.9 Bon à savoir

- **Aucune donnée ne quitte votre poste** en usage normal.
- Le **rapport d'audit** (optionnel) contient les valeurs d'origine : à protéger.
- Un **nom manqué** par la détection ? Ajoutez-le à la main via la sélection de
  texte (mode Texte / PDF).
- **CSV mal interprété** ? Vérifiez l'encodage (Latin-1 / UTF-8) et le séparateur.

---

## 3. Argumentaire commercial

### 3.1 Pourquoi anonymiser est devenu incontournable

Chaque jour, des données personnelles circulent hors de l'entreprise sans que
personne ne l'ait vraiment décidé : un extrait de comptabilité envoyé à un
prestataire, un fichier client collé dans un e-mail, un document glissé dans un
outil d'IA en ligne pour « gagner du temps ». **Chacun de ces gestes est un
transfert de données personnelles** — et engage la responsabilité de
l'organisation.

Le **RGPD** impose de ne traiter et de ne transmettre que les données strictement
nécessaires, et de les **minimiser**. Transmettre un nom, une adresse, un IBAN ou un
numéro de sécurité sociale qui n'ont pas lieu d'être exposés, c'est s'exposer à :

- des **sanctions** (jusqu'à 4 % du chiffre d'affaires annuel),
- une **perte de confiance** des clients, adhérents et partenaires,
- des **fuites** en cas de compromission du destinataire ou de l'outil en ligne.

Le risque le plus insidieux est aujourd'hui l'usage des **IA génératives en ligne** :
coller un fichier réel dans un service cloud, c'est **exporter des données
personnelles vers un tiers**, souvent hors UE, sans base légale ni maîtrise de leur
réutilisation. **Anonymiser avant de partager n'est plus une précaution : c'est une
obligation de conformité — et une hygiène numérique élémentaire.**

### 3.2 La réponse Anonymator : le 100 % local comme argument fort

Là où la plupart des solutions envoient vos données vers un serveur pour les
analyser, **Anonymator ne transmet rien**. Tout — détection **et** masquage —
s'exécute sur le poste de l'utilisateur. **La donnée sensible ne sort jamais.**

C'est un argument commercial **décisif** face aux services cloud : avec Anonymator,
la question « *mais où partent mes données pendant l'anonymisation ?* » ne se pose
plus. La réponse est : **nulle part.** Pas de compte, pas d'abonnement au débit, pas
de dépendance réseau après l'installation, pas de zone grise juridique.

### 3.3 Deux moteurs de détection, pour ne rien laisser passer

La force d'Anonymator tient à la **combinaison de deux technologies
complémentaires** :

- **La détection par règles**, chirurgicale, pour tout ce qui a un format connu :
  e-mails, téléphones, IBAN, SIREN/SIRET, numéros de sécurité sociale. Chaque
  détection est **validée par sa clé de contrôle** (clé de Luhn, modulo 97…) : très
  peu de faux positifs, une précision quasi parfaite sur ces données.

- **La détection intelligente par IA**, pour tout ce qui **échappe aux règles** :
  les noms de personnes, les adresses rédigées en toutes lettres, les
  organisations. C'est là qu'intervient un modèle d'IA de pointe.

Ensemble, ces deux moteurs couvrent aussi bien la donnée **structurée** que la
donnée **noyée dans du texte libre** — le point aveugle de la plupart des outils.

### 3.4 GLiNER : une IA de pointe… et française

Anonymator embarque **GLiNER**, l'un des modèles de reconnaissance d'entités
nommées **open source les plus reconnus au monde** — et **issu de la recherche
française**. Dans un secteur écrasé par les géants américains, c'est une **brique
d'IA souveraine**, développée en France, que nous mettons au service de la
protection de vos données.

Ses atouts, traduits en bénéfices :

- **Léger** : il tourne sur un simple PC, sans carte graphique ni serveur. D'où le
  fonctionnement **100 % local**.
- **Souple** : il détecte à la demande les catégories qu'on lui indique, sans
  réentraînement — l'outil s'adapte à vos besoins.
- **Performant** : une précision de niveau état de l'art sur la détection des noms
  et entités.

Choisir Anonymator, c'est donc s'appuyer sur une **technologie souveraine, libre et
maîtrisée**, sans boîte noire ni dépendance à un fournisseur étranger.

### 3.5 Un outil, plusieurs modules — un tour d'horizon

- **Module Texte** — le presse-papier de la conformité : on colle, on nettoie, on
  partage. Idéal avant d'utiliser une IA en ligne ou d'envoyer un e-mail.
- **Module Fichier** — traite les formats du quotidien (`.txt`, `.csv`, `.xlsx`,
  `.docx`, `.pptx`) en **préservant la mise en forme** : un tableur anonymisé reste
  un tableur exploitable, formules et onglets intacts.
- **Module PDF** — le **caviardage réel** : le texte sensible n'est pas juste
  recouvert, il est **détruit** dans le fichier. Un PDF que l'on peut transmettre en
  confiance, sans risque de « rectangle noir qui se retire ».
- **Module Règles métier** — l'outil parle **votre langage** : protégez vos
  références internes, forcez le masquage de vos codifications maison. L'IA
  générique devient un outil sur mesure.
- **Module Paramètres** — vous décidez **exactement** ce qui est détecté, catégorie
  par catégorie, et où vont les fichiers.
- **Rapport d'audit** — une **preuve** de ce qui a été anonymisé, exportable, pour
  documenter votre conformité.

### 3.6 En résumé — pourquoi choisir Anonymator

| Bénéfice | Ce que cela signifie pour vous |
|----------|-------------------------------|
| **100 % local** | Vos données ne quittent jamais votre poste. Conformité et confidentialité par conception. |
| **Deux moteurs de détection** | Aussi efficace sur les formats normés que sur les noms noyés dans le texte. |
| **IA GLiNER souveraine** | Une brique d'IA française, libre, sans boîte noire ni dépendance étrangère. |
| **Multi-formats, mise en forme préservée** | Vos fichiers restent exploitables après anonymisation. |
| **Caviardage PDF réel** | Le texte sensible est détruit, pas seulement masqué. |
| **Règles métier** | L'outil s'adapte à vos conventions internes. |
| **Sans installation lourde ni abonnement** | Un exécutable autonome, pas de compte, pas de serveur. |
| **Logiciel libre (AGPL)** | Code auditable, pérennité, maîtrise. |

**Anonymiser avant de partager, c'est protéger vos clients, votre organisation et
votre réputation. Anonymator le fait simplement, localement, et sans compromis sur
la confidentialité.**

---

*Document généré pour Anonymator v0.3.0 — susceptible d'évoluer avec l'application.
Se référer au dépôt <https://github.com/gudr-perso/Anonymator> pour la version à
jour.*
