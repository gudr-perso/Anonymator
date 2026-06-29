# Anonymator — Doc de conception (v1)

> Application locale Windows d'**anonymisation** de texte et de fichiers comptables.
> Issu d'un document d'inspiration, retravaillé en brainstorming le 2026-06-29.
> Ce doc fait foi sur les décisions ; il **diverge volontairement** du document d'inspiration sur plusieurs points (voir §11).

---

## 1. Objectif & périmètre v1

Protéger les données personnelles (PII) avant tout traitement externe, **en local**.

**Dans la v1 :**
- **Anonymisation (non réversible)** de **texte libre** et de **fichiers** éditables (.txt, .csv, .xlsx).
- Détection PII → remplacement par étiquettes de catégorie (`[PERSONNE]`, `[EMAIL]`, …).
- **Revue humaine interactive** avant masquage.
- **Rapport d'audit** exportable (CSV/JSON).
- **Thème commutable** (deux identités de marque).

**Reporté en v2 (hors périmètre v1) :**
- Pseudonymisation réversible (tokens `⟦PERSON_001⟧`, vault).
- Relais en ligne vers l'API Anthropic + dé-pseudonymisation.
- Stockage sécurisé de clé API (DPAPI).
- Tout composant Ollama (**supprimé**, voir §11).

**Hors périmètre v1 :** images, fichiers non éditables ; traitement par lot multi-documents ; cohérence inter-documents.

**Piste pour une version ultérieure — PDF :** envisageable mais comme **module dédié** (logique propre), pas une extension du moteur actuel.
- PDF texte natif → détection possible, mais réécriture en préservant la mise en page difficile → privilégier le **caviardage** (rectangles opaques sur les zones PII) plutôt que le remplacement par étiquette.
- PDF scanné → nécessite de l'**OCR** (dépendance + fiabilité à part).

### Principes directeurs
- **Le détecteur propose, le code dispose** : toute substitution/validation critique est déterministe.
- **Aucune PII ne sort de la machine** : traitement 100 % local en v1 (aucun appel réseau hormis le téléchargement initial du modèle GLiNER).
- **Irréversibilité assumée** : l'anonymisation remplace, sans table de correspondance conservée. Le rapport d'audit (qui, lui, contient des valeurs sensibles) est optionnel et signalé comme tel.

---

## 2. Stack technique

| Élément | Choix |
| --- | --- |
| Langage / UI | Python 3.11+ · PySide6 (Qt) |
| Packaging | PyInstaller (exe Windows) |
| Détection « floue » (noms/adresses/orgs) | **GLiNER** (NER zero-shot multilingue, modèle local ~200–500 Mo, Apache 2.0) |
| Détection déterministe | regex + checksums maison |
| Parsing fichiers | `csv` (stdlib) + sniffing · `openpyxl` (xlsx, édition en place) · lecture texte brut |
| Plateforme | Windows uniquement (v1) |

Le modèle GLiNER **n'est pas embarqué dans l'exe** : il est téléchargé au 1er lancement (exe léger, modèle découplé).

> Pas d'Ollama, pas de service externe : Anonymator est autonome côté détection.

---

## 3. Architecture applicative

### 3.1 Modules
```
ui/         écrans PySide6 (accueil, revue texte, revue fichier, paramètres) + thèmes QSS
core/       orchestrateur : détecter → fusionner → revue → appliquer → exporter
detectors/  deterministic.py (regex+checksum) · gliner_ner.py · merge.py (fusion/chevauchements)
files/      csv_io.py (sniff séparateur+encodage) · xlsx_io.py (openpyxl en place) · txt_io.py
report/     génération du rapport d'audit (CSV/JSON)
config/     référentiel d'entités (JSON) · préférences (thème, dossier de sortie)
```

Chaque module a une responsabilité unique et une interface claire, testable isolément.

### 3.2 Moteur de détection (cœur, partagé texte + fichier)
```
entrée → [valeurs uniques (dédup)]
       → couche déterministe  ∥  GLiNER
       → fusion
       → liste d'entités { type, valeur, start, end, source, confiance }
```
- **Dédup batch** : on ne détecte qu'une fois chaque **valeur unique** (cf. §6.3), puis on réapplique le résultat à toutes ses occurrences. Gain majeur sur les fichiers comptables très répétitifs.
- **Fusion (idée empruntée à Presidio, sans le framework)** : en cas de chevauchement, **priorité aux règles déterministes validées** ; à défaut, plus haute confiance ; suppression des spans contenus ; remplacement des chaînes les plus longues d'abord (éviter « Martin » dans « Martine »).

---

## 4. Détection PII

### 4.1 Couche déterministe (regex + checksum)
Détection + **validation** :
- Email, téléphone (FR + international), code postal FR, URL.
- IBAN (checksum **mod 97**), BIC.
- NIR (format + clé), SIREN/SIRET (**Luhn**).

Développée en **TDD** : chaque règle prouvée sur des exemples avant d'être acceptée.

### 4.2 Couche GLiNER (entités floues)
Labels en français passés au modèle : `personne`, `adresse postale`, `organisation` (extensible via le référentiel §7).
GLiNER renvoie des **spans fiables** (`start/end`) — on ne dépend pas d'offsets hallucinés par un LLM de chat.

### 4.3 Référentiel d'entités (table de paramétrage)
Piloté par un **fichier JSON** éditable dans Paramètres. Champs par entrée :
`code · libellé · méthode (Regex|LLM/NER|Hybride) · validation · actif · étiquette · sensibilité (Haute/Moyenne/Basse)`.
Profil par défaut verrouillé + surcharges utilisateur. (Le champ « préfixe token » de pseudonymisation est réservé v2.)

---

## 5. Mode TEXTE (anonymisation)

1. Zone de saisie multi-lignes → bouton **Analyser**.
2. Détection → **écran de revue couleur** : chaque entité surlignée selon sa **couleur de type** (jeu fixe, indépendant du thème), liste latérale des types avec compteurs et cases à cocher.
3. L'utilisateur **décoche** ce qu'il ne faut pas masquer, **sélectionne du texte** pour ajouter une entité manquée. La légende de type sert aussi de filtre global (cocher/décocher un type entier).
4. **Appliquer** → remplacement par `[CATÉGORIE]`.
5. Actions : copier, exporter `.txt`, exporter le rapport d'audit.

---

## 6. Mode FICHIER (anonymisation)

### 6.1 Types acceptés
`.txt`, `.csv`, `.xlsx`. Refus explicite et message clair pour les autres (ex. PDF).

### 6.2 Lecture robuste (leçons des fichiers réels)
- **Détection du séparateur** (sniffing) : ne pas présumer. Constaté : FEC en `|`, grand livre en `;`.
- **Détection de l'encodage** : fichiers comptables souvent **Latin-1 / cp1252**, pas UTF-8. Réécriture dans **le même encodage**.
- Gestion de l'absence éventuelle de ligne d'en-tête.

### 6.3 Sélection des colonnes analysées — **règle D**
- **Par défaut (règle A)** : analyser tout le texte **sauf** les colonnes purement numériques / dates / codes (montants, n° de compte, dates, n° de pièce).
- **+ surcharge utilisateur** : dans l'aperçu, cases pour **inclure/exclure** des colonnes.
- PII réelle attendue surtout dans `CompAuxLib` (nom du tiers) et `EcritureLib` (libellé libre) pour un FEC ; `CompteLib` souvent générique.

### 6.4 Traitement & préservation
- **.txt** : traitement texte intégral.
- **.csv** : parsing par colonnes, structure/séparateur/encodage préservés.
- **.xlsx** : **édition en place via openpyxl** (charger le classeur, ne modifier que les cellules ciblées). **Pas de round-trip pandas** (qui détruirait styles, formules, formats). Tous les onglets traités ; ordre, noms d'onglets et mise en forme conservés.
- Cellules non masquées préservées **à l'identique** (espaces de cadrage, virgule décimale, formats numériques).

### 6.5 Aperçu & enregistrement
- Aperçu tableau (csv/xlsx) ou texte (txt) ; navigation entre onglets pour un xlsx ; liste des entités masquées.
- Enregistrement dans un **nouveau fichier, même format**, jamais d'écrasement de l'original :
  `<nom_origine>_ano_AAAAMMJJHHMMSS.<ext>` dans le **dossier de sortie** paramétrable.

---

## 7. Rapport d'audit (v1, décision A)
- Liste des remplacements : type d'entité, valeur masquée, nombre d'occurrences, emplacement (colonne/onglet ou ligne).
- Export **CSV et/ou JSON**. Disponible en mode texte et fichier.
- **Avertissement** : contient des valeurs sensibles (table de ré-identification de fait) ; non inclus par défaut dans des envois externes ; à stocker/partager avec précaution.

---

## 8. Identité visuelle & thèmes

- **Deux thèmes de marque commutables** (Paramètres → Apparence), choix **persistant**. **Défaut au 1er lancement : France Cuma Numérique (vert).**
- Implémentation par **tokens de couleur** réassignés selon le thème (QSS paramétrée) → ajout d'un 3ᵉ thème trivial.

| Token | CAP Consulting (bleu) | France Cuma Numérique (vert) |
| --- | --- | --- |
| Primaire | `#1DA8E2` | `#31B700` (adoucissable vers `#00965E`) |
| Action/contraste | `#1570B8` | `#00965E` |
| Fond sombre | `#0D1A35` | `#063b27` |
| Accent | `#E8621A` (orange) | `#93C90E` (vert lime — **pas d'orange**) |
| Pastel/territoire | — | `#B1DCE2` |

- **Invariants quel que soit le thème** : polices (**titres Space Grotesk**, **texte Inter**) ; **couleurs fonctionnelles de détection** (Personne/Adresse/E-mail/IBAN… = jeu fixe, repère couleur=type) ; structure des écrans.
- **Gouvernance** : ne jamais mélanger les deux univers dans une même communication ; le thème suit l'entité propriétaire de l'usage.

---

## 9. Gestion des erreurs (cas couverts)
- Encodage inattendu / séparateur ambigu.
- xlsx : cellules formules, colonnes vides, multi-onglets.
- Fichier non supporté / corrompu (refus PDF clair).
- Modèle GLiNER absent → téléchargement guidé au 1er lancement.
- Texte très long → découpage en chunks **sans couper une entité** à la frontière.

---

## 10. Tests & évaluation
- **Corpus étiqueté** à partir des fichiers réels fournis (FEC `|`/Latin-1, grand livre `;`/Latin-1) + un `.txt` fictif riche en PII.
- **Plancher de rappel mesuré** sur les entités de sensibilité **Haute** (un nom manqué = fuite).
- **TDD** systématique sur les checksums (mod 97, Luhn, clé NIR) et la logique de fusion/substitution.

---

## 11. Écarts assumés vs document d'inspiration
1. **Ollama supprimé** : remplacé par GLiNER (NER spécialisé, spans fiables, batch rapide, pas de service externe). Tout le §4 « Gestion d'Ollama » du doc d'origine tombe.
2. **Pas de détection PII par LLM de chat** : on n'utilise pas de sortie JSON fragile ni de parsing défensif d'un LLM ; GLiNER fournit directement les spans.
3. **xlsx en place (openpyxl)** au lieu d'un round-trip pandas, pour réellement préserver la mise en forme.
4. **v1 = anonymisation seule** : pseudonymisation/vault/Anthropic explicitement reportés.
5. **Vocabulaire** : on parle de réduction de risque / masquage, pas d'« anonymisation RGPD » irréversible garantie (le rapport d'audit reste une table de ré-identification).
6. **Thème multi-marques** (CAP/CUMA) ajouté, non prévu à l'origine.

---

## 12. Points ouverts (à préciser à l'implémentation)
- Liste finale des entités **actives** par défaut en v1 (depuis le référentiel §4.3).
- Politique sur les **noms d'organisations bancaires** récurrents (« Crédit Agricole ») : masqués ou non par défaut (réglable via toggle ORG).
- Stratégie exacte de **chunking** du texte très long (seuil, recouvrement).
- Faut-il un **versionnage git** du projet (non initialisé à ce jour).
