# Documentation Anonymator

> Version du document : 2.0 — correspond à Anonymator **v0.5.1**
> Licence : AGPL-3.0-or-later · Code source : <https://github.com/gudr-perso/Anonymator>
> Documentation **utilisateur** de la même version, publiée en ligne :
> <https://capconsulting.notion.site/anonymator-documentation-utilisateur>

Anonymator est une application **Windows 100 % locale** qui détecte et masque les
données personnelles et sensibles (noms, adresses, e-mails, IBAN, numéros de
sécurité sociale, mots de passe…) dans du texte et des fichiers bureautiques,
**sans qu'aucune donnée ne quitte le poste de travail**.

> **Nom du produit.** *Anonymator* est le nom du **projet**. L'application est
> diffusée en plusieurs **éditions**, chacune avec son propre nom de produit, son
> thème de couleurs, son archive et son exécutable — pour un fonctionnement
> strictement identique. Ce document parle donc du projet et de « l'application ».
> Le mécanisme est détaillé en §1.3.

Cette documentation est organisée en trois parties :

1. [Documentation technique](#1-documentation-technique) — stack, modèles, méthodes de détection, architecture, licences.
2. [Documentation fonctionnelle](#2-documentation-fonctionnelle) — installation et prise en main, écran par écran.
3. [Argumentaire commercial](#3-argumentaire-commercial) — pourquoi anonymiser, ce que l'outil apporte.

---

## 1. Documentation technique

### 1.1 Vue d'ensemble

Anonymator est un logiciel de bureau autonome. Il fonctionne **hors ligne** après
une unique phase d'initialisation (téléchargement du modèle d'intelligence
artificielle). Le traitement — détection comme masquage — s'effectue intégralement
sur la machine de l'utilisateur : aucun appel réseau n'est émis en usage normal.

Le geste central du produit est la **revue humaine** : l'application détecte, mais
c'est l'utilisateur qui valide, valeur par valeur, avant que quoi que ce soit ne
soit remplacé. Le traitement est une **anonymisation non réversible** — il n'y a ni
coffre de correspondance, ni dé-anonymisation.

### 1.2 Stack technique

| Couche | Technologie | Rôle |
|--------|-------------|------|
| Langage | **Python ≥ 3.11** (3.14 sur le poste de développement) | Cœur applicatif |
| Interface graphique | **PySide6 (Qt 6)** | Fenêtre, écrans, thèmes |
| Détection IA (NER) | **GLiNER** — modèle `urchade/gliner_multi-v2.1` | Noms, adresses, organisations |
| Moteur IA sous-jacent | **PyTorch / Hugging Face Transformers** | Exécution du modèle GLiNER |
| PDF | **PyMuPDF** (© Artifex) | Lecture, caviardage réel, extraction |
| Tableur | **openpyxl** | Lecture/écriture `.xlsx` (styles, formules, onglets préservés) |
| Bureautique Office | **python-docx**, **python-pptx** | Traitement `.docx` et `.pptx` (OOXML) |
| Certificats | **truststore** | Validation TLS via le magasin Windows (antivirus inspectant le HTTPS) |
| Packaging | **PyInstaller** (`anonymator.spec`) | Génération de l'exécutable Windows autonome |
| Tests | **pytest**, **pytest-qt** | 99 fichiers de test — **615 tests verts**, 1 d'intégration désélectionné |

L'application est distribuée sous forme d'un **exécutable Windows autonome**,
produit par PyInstaller à partir du fichier de spécification `anonymator.spec`.
Aucune installation de Python n'est requise sur le poste cible.

**Distribution du modèle IA.** Le modèle GLiNER (~2,2 Go) n'est **pas** embarqué
dans l'exécutable. Il est téléchargé au premier lancement depuis Hugging Face et
mis en cache localement dans `%USERPROFILE%\.cache\huggingface`. Les lancements
suivants s'effectuent hors ligne, et le cache **survit** à une mise à jour de
l'application.

### 1.3 Éditions et marques

Une **marque** (`anonymator/brand.py`) est une surcouche du thème qui fige, pour un
exécutable diffusé : le **thème imposé**, le **nom de produit affiché** (titre de
fenêtre, en-tête, écran À propos) et le **nom du fichier exe**.

| Clé | Thème | Verrouillée |
|-----|-------|-------------|
| `cuma` | vert | oui |
| `cap` | bleu | oui |
| `dev` | issu des préférences | non |

Une édition verrouillée **masque le sélecteur de thème** dans les Paramètres — le
verrou est purement UI, les deux thèmes restent présents dans le binaire. Le mode
`dev` (non diffusé) conserve le sélecteur.

Le build est paramétré par la variable d'environnement `ANONYMATOR_BUILD_BRAND`,
lue par `anonymator.spec` via `brand.build_target()`, qui choisit le point d'entrée
verrouillé (`anonymator/brands/cap.py` ou `cuma.py`), le nom d'exe et l'icône.
`scripts/build.ps1 cap|cuma|dev|all` enchaîne build, copie du `LICENSE` et du
dossier `exemples/` à la racine du dossier distribué, puis zip.

### 1.4 Qu'est-ce que le NER ?

Le **NER** (*Named Entity Recognition*, ou « reconnaissance d'entités nommées »)
est une tâche de traitement automatique du langage naturel qui consiste à
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

### 1.5 Qu'est-ce que GLiNER ?

**GLiNER** (*Generalist and Lightweight model for Named Entity Recognition*) est un
modèle de reconnaissance d'entités nommées **open source**, reconnu comme l'une
des références du domaine. Il a été conçu et publié par une équipe de recherche
**française** (travaux d'Urchade Zaratiana et de ses co-auteurs, menés en France).

**Comment il fonctionne.** Contrairement aux modèles de NER classiques, entraînés
sur une liste **figée** de catégories, GLiNER est un modèle **« zero-shot »** : on
lui fournit, au moment de l'analyse, la **liste des types d'entités recherchés en
langage naturel** (« personne », « adresse postale », « organisation »). Le modèle
compare chaque portion du texte à ces libellés et renvoie les correspondances avec
un **score de confiance**. Cette souplesse permet d'ajuster ce que l'on cherche
sans réentraîner le modèle.

Techniquement, GLiNER repose sur un **transformeur bidirectionnel** (famille BERT)
qui encode simultanément le texte et les libellés de types, puis mesure leur
adéquation. Il est **léger** — il tourne sur un simple CPU, sans carte graphique —
tout en restant compétitif face à des modèles bien plus lourds. C'est cette
combinaison **précision / légèreté / exécution locale** qui le rend idéal pour un
outil de bureau confidentiel.

Le modèle utilisé est `urchade/gliner_multi-v2.1`, une variante **multilingue**
(dont le français), publiée sous licence **Apache-2.0** (usage commercial autorisé).

> **Note d'implémentation — le *chunking*.** GLiNER tronque silencieusement toute
> entrée dépassant ~384 tokens (environ 1 500 caractères de français dense) :
> au-delà, le bas du texte n'est jamais analysé. Anonymator découpe donc les longs
> textes en segments < 1 000 caractères (`core/chunking.py`), en coupant sur les
> espaces, puis rebase les positions des entités détectées. Seul le NER est
> découpé : la détection déterministe voit toujours le texte entier (un IBAN coupé
> en deux ne serait plus reconnu).

> **Mode dégradé.** Le chargement du modèle n'est jamais bloquant. Sans modèle,
> `ner.NullNer` prend la place de `GlinerDetector` : l'application démarre, toutes
> les détections par règles fonctionnent, et une bannière signale l'absence de la
> détection intelligente. Le téléchargement peut être lancé depuis l'accueil ou les
> Paramètres, **sans redémarrage**.

### 1.6 Les méthodes de détection

Anonymator combine plusieurs approches complémentaires, dont les résultats sont
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
fixe** — noms de personnes, adresses en prose, organisations.

**c) Détecteurs contextuels et par entropie (secrets).** `secrets_detect.py` repère
les **identifiants et mots de passe** de deux façons : par **mots-clés contextuels**
(« mot de passe : … », « login … ») et par **analyse d'entropie** (un jeton mêlant
minuscules, majuscules et chiffres est traité comme un secret probable).

**d) Règles métier de l'utilisateur.** Moteur symétrique `keep` (allow-list) /
`mask` (force-list → `[REGLE-INTERNE]`), par motif simple (jokers) ou expression
régulière (`user_rules.py`). Voir §2.7.

**Fusion et priorité.** Toutes les détections passent par un moteur de fusion
(`merge.py`) qui **élimine les chevauchements** selon un ordre de priorité :
détection déterministe / règle métier d'abord, puis score de confiance, puis
longueur du segment. `dedup.py` garantit qu'une même valeur n'est présentée qu'une
fois. Le remplacement final substitue à chaque valeur retenue l'**étiquette de sa
catégorie**, de la fin du texte vers le début pour préserver les positions.

### 1.7 Le raisonnement par colonne (CSV / XLSX)

Sur un tableau, envoyer chaque cellule isolément au modèle donne des résultats
incohérents (un nom sur deux masqué, une ville oui et l'autre non).
`files/columns.py` décide donc un **plan par colonne** avant toute détection :

| Politique | Déclencheur | Effet |
|---|---|---|
| `TYPED` | type connu par l'en-tête, ou contenu homogène | la cellule entière est l'entité, le NER n'est pas appelé |
| `TEXT` | colonne libre | règles + NER |
| `SKIP` | mesures numériques, nomenclatures | hors périmètre |

Garde-fous : **plein-cadre** (une colonne numérique n'est typée que si l'entité
couvre toute la cellule — `15866,00` n'est pas un code postal), garde
**« identifiant »** (`code_client`, `CompteNum`… jamais typés d'office), et
**cardinalité à deux critères** (ratio *et* plafond absolu, pour ne pas confondre un
client répété sur 100 000 écritures avec une nomenclature).

**Hypothèse d'en-tête.** `csv.Sniffer` est instable (il voit un en-tête avec une
ligne de données, plus aucun avec deux) : un interrupteur **« Première ligne =
en-têtes »** laisse l'utilisateur trancher (`has_header` sur `anonymize_csv` /
`anonymize_file`). Côté XLSX, `sheet_has_header` s'appuie sur les **types réels des
cellules** — une ligne de titres est textuelle au-dessus d'au moins une colonne qui
ne l'est pas — et retombe sur le lexique de noms de colonnes si la feuille est
entièrement textuelle.

**Forçage manuel.** Un clic sur l'en-tête ouvre un menu à trois états :

| Mode | Effet |
|---|---|
| `AUTO` | rend la colonne à son plan calculé (défaut) |
| `MASK` | **toutes** les cellules non vides masquées, avec un type à choisir |
| `CLEAR` | la colonne sort du périmètre |

Le forçage est une **décision explicite de l'utilisateur devant son fichier** : il
**prime sur le référentiel**. `detect_column(..., force=True)` court-circuite le
garde `is_active`, et le sous-menu propose **tous** les types — les inactifs
signalés « (inactif) », le type déduit en tête marqué « (déduit) » — plus une entrée
neutre **« Masquer (neutre) → `[MASQUÉ]` »** pour les colonnes sans type sémantique.
D'où `Referential.forceable_codes()`, distinct de `active_codes()` (qui, lui, sert à
la détection **automatique**, laquelle respecte l'état du référentiel). Les règles
utilisateur « conserver » restent prioritaires sur un forçage.

Un forçage **survit au changement d'hypothèse d'en-tête** s'il a encore un sens
(`has_column`), et est abandonné en silence sinon.

### 1.8 Les sessions de revue

La comptabilité type/valeur qui alimente l'arbre « Entités détectées » et ses cases
est factorisée dans une hiérarchie unique :

```
ReviewSessionBase            socle : comptabilité type/valeur, filtres partagés
 ├─ TabularReviewSession     tableaux : entités par cellule, arbitrages par colonne
 │   ├─ FileReviewSession        CSV      — clé cellule (ligne, colonne)
 │   └─ XlsxReviewSession        classeur — clé cellule (feuille, ligne, colonne)
 └─ OoxmlReviewSession        docx/pptx — clé = index d'unité
```

`_index()` est **rejouable** : tout est recalculé à chaque changement en conservant
les arbitrages pris — jamais de compte différentiel, qui finit toujours par dériver.
Toutes les sessions exposent `apply_and_save(out_path)` : l'écran n'a pas à savoir
de quel format il s'agit pour enregistrer.

Pour le XLSX, `anonymize_workbook` est scindé en **`scan_workbook` / `apply_workbook`**,
avec un `XlsxScanResult` qui garde le classeur openpyxl ouvert en mémoire (mise en
forme et formules préservées). C'est cette césure qui rend la revue possible :
l'utilisateur tranche entre les deux. Le chemin direct sans revue enchaîne
simplement les deux appels.

Chaque traitement lourd tourne hors du thread graphique, dans un `QThread` dédié
(`file_scan_worker`, `xlsx_scan_worker`, `ooxml_scan_worker`, `pdf_scan_worker`,
`text_analyze_worker`, `file_anonymize_worker`, `download_worker`).

### 1.9 Référentiel des entités et niveau de risque

Les types d'entités sont déclarés dans `anonymator/config/entities.json`. Chaque
type porte une **méthode** de détection, une **étiquette** de remplacement, un état
**actif/inactif** par défaut et une **sensibilité** (Haute / Moyenne / Basse).

| Code | Libellé | Méthode | Étiquette | Sensibilité | Actif |
|------|---------|---------|-----------|-------------|-------|
| PERSON | Personne | NER | `[PERSONNE]` | Haute | oui |
| ADDRESS | Adresse | NER | `[ADRESSE]` | Haute | oui |
| ORG | Organisation | NER | `[ORG]` | Moyenne | oui |
| EMAIL | E-mail | déterministe | `[EMAIL]` | Haute | oui |
| PHONE | Téléphone | déterministe | `[TEL]` | Haute | oui |
| IBAN | IBAN | déterministe | `[IBAN]` | Haute | oui |
| BIC | BIC / SWIFT | déterministe | `[BIC]` | Moyenne | **non** |
| SIREN | SIREN | déterministe | `[SIREN]` | Moyenne | oui |
| SIRET | SIRET | déterministe | `[SIRET]` | Moyenne | oui |
| NIR | N° sécu | déterministe | `[NIR]` | Haute | oui |
| POSTAL_CODE | Code postal | déterministe | `[CP]` | Basse | **non** |
| URL | URL | déterministe | `[URL]` | Basse | **non** |
| LOGIN | Identifiant | contextuel | `[LOGIN]` | Haute | oui |
| PASSWORD | Mot de passe | contextuel | `[SECRET]` | Haute | oui |
| REGLE_INTERNE | Règle interne | règle | `[REGLE-INTERNE]` | Moyenne | oui |
| MASK | Masquer (neutre) | manuel | `[MASQUÉ]` | Basse | **non** |

`MASK` est un **pseudo-type** : jamais produit par la détection automatique, il
n'existe que pour le forçage manuel d'une colonne sans type sémantique. `BIC`,
`POSTAL_CODE` et `URL` sont implémentés mais **inactifs par défaut** (bruyants sur
des extractions comptables) ; ils s'activent dans les Paramètres.

La **sensibilité la plus élevée** parmi les entités retenues détermine un **niveau
de risque global** (`core/risk.py`) affiché à l'utilisateur (Élevé / Moyen /
Faible), pour guider la décision de partage.

### 1.10 Traçabilité — le rapport d'audit

Chaque session de revue sait produire un **rapport d'audit** (`report/audit.py`) :
pour chaque valeur remplacée, le type, la valeur originale, l'étiquette appliquée,
le nombre d'occurrences, les emplacements et le statut « confirmé ou non ».
`AuditReport` sait s'exporter en **CSV** ou **JSON**.

> ⚠️ **État réel en v0.5.1 : brique moteur, non exposée dans l'interface.** Les
> sessions construisent bien le rapport (il trace notamment la purge des
> métadonnées Office), mais **aucun écran ne propose de l'exporter**. C'est un
> candidat naturel pour une prochaine version — le code est prêt, il manque le
> bouton et l'emplacement d'export.

Quand il sera exposé : ce rapport contient les **valeurs d'origine en clair**. Il
constituera une pièce sensible, à stocker et partager avec les mêmes précautions
que la donnée source.

### 1.11 Formats de fichiers pris en charge

| Format | Traitement |
|--------|-----------|
| `.txt` | Texte intégral |
| `.csv` | Par colonnes (§1.7), séparateur auto-détecté, encodage préservé |
| `.xlsx` | Édition en place — styles, formules et onglets conservés ; revue feuille par feuille |
| `.docx` | Contenu OOXML (Word), remap des *runs*, **+ purge des métadonnées d'identité** |
| `.pptx` | Contenu OOXML (PowerPoint), idem |
| `.pdf` (natif) | **Caviardage réel** (destruction du texte sous le rectangle) **ou** extraction `.txt` |
| `.pdf` (scanné, image seule) | Non supporté — message explicite, aucun plantage (pas d'OCR) |

Les anciens formats binaires `.doc`, `.xls`, `.ppt` ne sont pas pris en charge.

Le fichier **original n'est jamais modifié** : la sortie est écrite sous le nom
`<nom>_ano_AAAAMMJJHHMMSS.<ext>` (`output_naming.py`), dans le dossier de sortie
configuré ou, à défaut, **dans le dossier du fichier d'origine**.

**PDF.** PyMuPDF est isolé dans `anonymator/files/pdf/`. Le caviardage est une
**rédaction juridique réelle** (le texte sous le rectangle est détruit, pas
recouvert), précédée d'une **revue visuelle obligatoire** et d'une confirmation. Les
valeurs confirmées sont **propagées à tout le document** en respectant l'ordre de
lecture. Les zones tracées à la main n'existent que pour le caviardage : elles ne
sont pas reportées dans une extraction `.txt`, et l'utilisateur en est averti.

### 1.12 Emplacements sur le poste

| Quoi | Où |
|---|---|
| Préférences (thème, dossier de sortie, catégories actives) | `%USERPROFILE%\.anonymator\preferences.json` |
| Règles métier de l'utilisateur | `%USERPROFILE%\.anonymator\user_rules.json` |
| Modèle GLiNER | `%USERPROFILE%\.cache\huggingface` |
| Fichiers anonymisés | Dossier de sortie choisi, ou dossier du fichier d'origine |

Tous sont **hors du dossier de l'application** : ils survivent à une mise à jour,
qui consiste simplement à dézipper la nouvelle archive.

### 1.13 Licences et modèle de distribution

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

> **Modèle économique.** Le choix de l'AGPL (dépôt public), imposé par PyMuPDF, est
> cohérent avec une monétisation par la **prestation de service** (déploiement,
> adaptation, accompagnement, règles métier sur mesure) plutôt que par la vente de
> licences — inopposable en AGPL.

**Décisions verrouillées.** v1 = **anonymisation seule** (pseudonymisation, vault et
relais LLM sont hors périmètre) ; détection floue = **GLiNER**, substitution
**déterministe** ; couleurs fonctionnelles par type d'entité **indépendantes du
thème** ; PDF **natifs uniquement**, revue visuelle obligatoire avant destruction ;
purge **systématique** des métadonnées Office.

### 1.14 Développement, tests et build

```
.venv/Scripts/python -m pytest -q        # 615 passed, 1 deselected
.venv/Scripts/python -m anonymator       # lancement en mode dev (sélecteur de thème actif)
scripts/build.ps1 cap|cuma|dev|all       # build PyInstaller + zip par édition (~4 min/édition)
```

Le test marqué `integration` (modèle GLiNER réel) est **désélectionné par défaut**
(`addopts` dans `pyproject.toml`) ; voir `docs/installation-gliner.md`. La
plateforme Qt *offscreen* est gérée automatiquement par `tests/conftest.py`.

`__version__` dans `anonymator/__init__.py` est la **source de vérité unique** de la
version, dupliquée dans `pyproject.toml` et lue au runtime par l'UI. Procédure de
publication : `docs/RELEASE.md`.

> **Piège de build :** ne pas rediriger la sortie de `build.ps1` avec une
> redirection de stderr. PyInstaller écrit ses `INFO` sur stderr, PowerShell les
> transforme en erreurs et l'arrêt sur erreur du script avorte le build dès la
> première ligne.

---

## 2. Documentation fonctionnelle

*Destinée à un nouvel utilisateur. Cette partie est la source de la
[documentation utilisateur publiée en ligne](https://capconsulting.notion.site/anonymator-documentation-utilisateur) ;
les deux doivent rester cohérentes.*

### 2.1 Prérequis

- **Windows** (poste bureautique standard, sans carte graphique dédiée)
- **Aucun droit administrateur**, aucune installation système
- Environ **1 Go d'espace disque** pour l'application, **+ 2,2 Go** si la détection
  intelligente est activée
- Une **connexion Internet**, une seule fois, pour ce téléchargement optionnel

### 2.2 Installation

Il n'y a pas d'installeur : l'application est un **exécutable autonome**.

1. **Télécharger** l'archive `.zip` de l'édition concernée.
2. **Dézipper** l'archive dans un dossier au choix (`Documents`, un lecteur réseau,
   une clé USB…).
3. **Double-cliquer sur le fichier `.exe`** situé à la racine du dossier dézippé —
   c'est le seul, et il porte le nom de l'édition.

Windows peut afficher un avertissement **SmartScreen** au premier lancement
(l'exécutable n'est pas signé numériquement) : *« Informations complémentaires »* →
*« Exécuter quand même »*.

À côté de l'exécutable, le dossier contient :

- `exemples\` — un **jeu de fichiers de démonstration** (données fictives) : un
  fichier client en `.csv` et en `.xlsx`, un compte rendu de réunion en `.pdf` ;
- `LICENSE` — le texte de la licence AGPL-3.0 ;
- `_internal\` — les composants techniques : ne rien y modifier.

### 2.3 Premier lancement — la détection intelligente

Au premier démarrage, un encart **« Activer la détection intelligente »** apparaît
en haut de l'écran d'accueil, avec **« Télécharger maintenant »** et
**« Plus tard »**.

Il s'agit du modèle **GLiNER** (~2,2 Go), qui sert à repérer ce qui n'a aucun format
fixe : noms de personnes, adresses rédigées en toutes lettres, organisations.
Téléchargé **une seule fois**, il est ensuite utilisé **hors ligne**.

**L'application fonctionne sans lui.** En **mode dégradé**, toutes les détections
par règles (e-mail, téléphone, IBAN, SIREN/SIRET, NIR, mots de passe…) sont
opérationnelles ; seuls les noms, adresses et organisations restent hors de portée.
Une bannière le rappelle, et le téléchargement peut être lancé plus tard depuis
l'accueil ou les Paramètres, **sans redémarrer**.

**Mise à jour de l'application** : pas de mise à jour automatique. On télécharge la
nouvelle archive, on la dézippe, on lance le nouvel exécutable. Préférences, règles
métier et modèle sont conservés (voir §1.12).

### 2.4 L'écran d'accueil

Menu **« Par où commencer ? »**, six entrées :

| Écran | À quoi il sert |
|---|---|
| **Coller du texte** | Analyser et masquer un texte collé |
| **Importer un fichier** | `.txt`, `.csv`, `.xlsx`, `.docx` ou `.pptx` |
| **Importer un PDF** | Caviarder ou extraire (PDF natifs) |
| **Paramètres** | Thème, dossier de sortie, types détectés, modèle |
| **Gestion des règles** | Règles métier |
| **À propos** | Licence, version et mentions |

Un **bandeau d'onglets** en haut de la fenêtre permet de passer d'un écran à l'autre
à tout moment.

### 2.5 Menu « Texte »

1. **Coller ou saisir** le texte dans la zone « Texte à anonymiser ».
2. **« Analyser »** : les entités sont **surlignées** (une couleur par catégorie) et
   **listées** sous « Entités détectées ».
3. **Revoir la sélection** : tout est coché par défaut ; on décoche ce que l'on veut
   conserver en clair, valeur par valeur ou catégorie entière.
4. Un **« Niveau de risque »** (Élevé / Moyen / Faible) résume la sensibilité de ce
   qui a été trouvé.
5. **« Appliquer le masquage »** → le « Résultat anonymisé » s'affiche.
6. **« Copier »** ou **« Exporter .txt »**.

**Valeurs à clé non conforme.** Une valeur au bon format dont la clé de contrôle ne
tombe pas juste est signalée `⚠ format valide mais clé mathématiquement fausse`,
surlignée en pointillé et **décochée par défaut** — c'est le plus souvent une valeur
factice ou une coquille. On peut la cocher pour la masquer quand même.

> Il n'y a **pas** d'ajout manuel d'entité par sélection de texte dans cet écran :
> les recours sont le forçage de colonne (mode Fichier), la « Zone manuelle »
> (mode PDF) et les règles métier.

### 2.6 Menu « Fichier »

Formats acceptés : `.txt`, `.csv`, `.xlsx`, `.docx`, `.pptx`.

1. **« Ouvrir »** → aperçu (grille pour un tableau, liste d'unités pour un document).
2. **« Analyser »**.
3. **Revoir** les entités (cases à cocher par valeur et par catégorie).
4. **« Anonymiser & enregistrer »**.

L'original n'est jamais modifié ; la sortie porte le suffixe `_ano_<horodatage>`
(§1.11).

**Périmètre du traitement (tableaux).** Le bloc « Périmètre du traitement » affiche
le plan retenu par colonne et **sa raison** (infobulle sur l'en-tête). Un **clic sur
l'en-tête** ouvre le menu : **Automatique** / **Tout anonymiser** (avec choix du
type — tous les types sont proposés, les inactifs signalés, plus l'entrée neutre
« Masquer (neutre) ») / **Tout libérer**. Le mécanisme complet est décrit en §1.7.

**Case « Première ligne = en-têtes ».** La changer modifie le périmètre des
colonnes : l'application demande de **relancer l'analyse**, et **reporte** les choix
déjà faits (valeurs décochées, catégories, colonnes forcées).

**Classeurs `.xlsx`.** Un **sélecteur de feuille** apparaît au-dessus de l'aperçu ;
la revue se fait une feuille à la fois, chaque feuille ayant **sa propre** hypothèse
d'en-tête. L'enregistrement traite **tout le classeur**. Une pagination
(« Première / ‹ Précédent / Suivant › / Dernière ») parcourt les lignes des gros
fichiers.

### 2.7 Menu « PDF »

Réservé aux **PDF natifs** (texte sélectionnable). Deux traitements :

- **Caviardage** — les zones détectées sont recouvertes et le texte situé dessous
  est **réellement supprimé** du fichier. Le résultat reste un PDF.
- **Extraction `.txt`** — le texte est extrait puis anonymisé comme en mode Texte.

Marche à suivre :

1. **« Ouvrir un PDF »**.
2. **« Analyser »** : les entités sont surlignées **sur l'aperçu** de la page.
3. Revoir (cases à cocher), page par page. Zoom : `Ctrl +` / `Ctrl −`, `Ctrl 0`
   pour 100 %, `Ctrl 9` pour ajuster à la largeur, `Ctrl` + molette.
4. **« Zone manuelle »** pour caviarder un tampon, une signature ou un logo que la
   détection ne peut pas voir.
5. Enregistrer — une **confirmation** rappelle que la rédaction détruit
   définitivement les données sélectionnées.

Les **zones manuelles n'existent que pour le caviardage** : en cas d'export `.txt`,
l'application prévient qu'elles ne seront pas reportées. Les **PDF scannés** (image
seule) ne sont pas pris en charge — pas d'OCR — et le message est explicite.

### 2.8 Menu « Gestion des règles »

Deux sens :

- **« Ne jamais masquer »** — protège une codification interne que la détection
  pourrait confondre avec une donnée personnelle.
- **« Toujours masquer »** — force le remplacement de tout ce qui correspond au
  motif, par l'étiquette `[REGLE-INTERNE]`.

Deux modes d'écriture des motifs :

| Mode | Syntaxe | Exemple |
|---|---|---|
| **Simple** | `#` = un chiffre · `?` = un caractère · `*` = n'importe quelle suite | `A#######`, `FACT.*` |
| **Expert** | Expression régulière complète | `^CL[0-9]{4}-[A-Z]{2}$` |

Les règles sont enregistrées sur le poste (§1.12) et appliquées à **toutes** les
analyses (texte, fichier, PDF). Le chemin du fichier est affiché en bas de l'écran
et le bouton **« Ouvrir le dossier »** y mène : c'est ce fichier que l'on **copie
d'un poste à l'autre** pour partager un jeu de règles. Un motif expert invalide est
refusé (« Expression régulière invalide ») et rien n'est enregistré.

### 2.9 Menu « Paramètres »

- **Général** — **Thème** (visible uniquement en mode dev ; verrouillé sur les
  éditions diffusées) et **Dossier de sortie** (laissé vide : le fichier est écrit à
  côté de son original).
- **Types d'entités à détecter** — une case par catégorie, avec un compteur des
  types actifs. C'est ici que l'on active BIC, code postal et URL, inactifs par
  défaut.
- **Modèle de détection intelligente** — état d'installation (`✅ Installé` avec sa
  taille, ou `⬜ Non installé`), emplacement du cache, bouton de **téléchargement**
  ou de **réparation** avec barre de progression.

### 2.10 Menu « À propos »

Version installée, licence **AGPL-3.0** avec lien vers le **code source au tag
correspondant à la version**, liste des **composants embarqués** et leur licence,
lien de contact.

### 2.11 Bon à savoir

- **Aucune donnée ne quitte le poste** en usage normal.
- **Relire le résultat** avant de le partager : aucune détection automatique n'est
  infaillible, c'est l'utilisateur qui valide.
- **Conserver l'original** : l'anonymisation est irréversible.
- Sur un fichier récurrent, **investir dans des règles métier** : les analyses
  suivantes seront justes du premier coup.
- Pour signaler un problème, **ne jamais envoyer le fichier source** — reproduire le
  cas sur un extrait fictif, ou sur le jeu livré dans `exemples\`.

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

C'est un argument commercial **décisif** face aux services cloud : la question
« *mais où partent mes données pendant l'anonymisation ?* » ne se pose plus. La
réponse est : **nulle part.** Pas de compte, pas d'abonnement au débit, pas de
dépendance réseau après l'installation, pas de zone grise juridique.

### 3.3 Deux moteurs de détection, pour ne rien laisser passer

- **La détection par règles**, chirurgicale, pour tout ce qui a un format connu :
  e-mails, téléphones, IBAN, SIREN/SIRET, numéros de sécurité sociale. Chaque
  détection est **validée par sa clé de contrôle** (Luhn, modulo 97…) : très peu de
  faux positifs.

- **La détection intelligente par IA**, pour tout ce qui **échappe aux règles** :
  noms de personnes, adresses rédigées en toutes lettres, organisations.

Ensemble, ces deux moteurs couvrent aussi bien la donnée **structurée** que la
donnée **noyée dans du texte libre** — le point aveugle de la plupart des outils.

### 3.4 GLiNER : une IA de pointe… et française

Anonymator embarque **GLiNER**, l'un des modèles de reconnaissance d'entités
nommées **open source les plus reconnus au monde** — et **issu de la recherche
française**. Dans un secteur écrasé par les géants américains, c'est une **brique
d'IA souveraine** mise au service de la protection des données.

- **Léger** : il tourne sur un simple PC, sans carte graphique ni serveur. D'où le
  fonctionnement 100 % local.
- **Souple** : il détecte à la demande les catégories qu'on lui indique, sans
  réentraînement.
- **Performant** : une précision de niveau état de l'art sur la détection des noms
  et entités.

### 3.5 Un outil, plusieurs modules

- **Module Texte** — le presse-papier de la conformité : on colle, on nettoie, on
  partage. Idéal avant d'utiliser une IA en ligne ou d'envoyer un e-mail.
- **Module Fichier** — traite les formats du quotidien (`.txt`, `.csv`, `.xlsx`,
  `.docx`, `.pptx`) en **préservant la mise en forme** : un tableur anonymisé reste
  un tableur exploitable, formules et onglets intacts. Les documents Office sont
  aussi **purgés de leurs métadonnées d'identité**.
- **Raisonnement par colonne** — sur une extraction comptable, l'outil décide
  **colonne par colonne** au lieu de traiter chaque cellule isolément : plus de
  « un nom sur deux masqué ». Et un simple clic sur un en-tête permet de **trancher
  à la main**, contre l'avis de l'outil.
- **Module PDF** — le **caviardage réel** : le texte sensible n'est pas seulement
  recouvert, il est **détruit** dans le fichier. Un PDF transmissible en confiance.
- **Module Règles métier** — l'outil parle **votre langage** : protégez vos
  références internes, forcez le masquage de vos codifications maison, partagez le
  fichier de règles au sein de l'équipe.
- **Module Paramètres** — vous décidez **exactement** ce qui est détecté, catégorie
  par catégorie, et où vont les fichiers.

### 3.6 En résumé

| Bénéfice | Ce que cela signifie pour vous |
|----------|-------------------------------|
| **100 % local** | Vos données ne quittent jamais votre poste. Conformité et confidentialité par conception. |
| **Deux moteurs de détection** | Aussi efficace sur les formats normés que sur les noms noyés dans le texte. |
| **IA GLiNER souveraine** | Une brique d'IA française, libre, sans boîte noire ni dépendance étrangère. |
| **Revue humaine systématique** | Rien n'est masqué sans votre validation, valeur par valeur. |
| **Multi-formats, mise en forme préservée** | Vos fichiers restent exploitables après anonymisation. |
| **Caviardage PDF réel** | Le texte sensible est détruit, pas seulement masqué. |
| **Règles métier** | L'outil s'adapte à vos conventions internes. |
| **Sans installation lourde ni abonnement** | Un exécutable autonome, pas de compte, pas de serveur. |
| **Logiciel libre (AGPL)** | Code auditable, pérennité, maîtrise. |

**Anonymiser avant de partager, c'est protéger vos clients, votre organisation et
votre réputation. Anonymator le fait simplement, localement, et sans compromis sur
la confidentialité.**

---

*Document rédigé pour Anonymator v0.5.1 — susceptible d'évoluer avec l'application.
Se référer au dépôt <https://github.com/gudr-perso/Anonymator> pour la version à
jour.*
