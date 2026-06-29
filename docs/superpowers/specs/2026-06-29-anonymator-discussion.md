# Anonymator — Journal de brainstorming

> Compagnon du doc de conception [2026-06-29-anonymator-design.md](2026-06-29-anonymator-design.md).
> Trace les questions, les options étudiées et **pourquoi** chaque décision a été prise.
> Date : 2026-06-29.

---

## Point de départ

Un document d'inspiration décrivait une app locale Windows d'anonymisation/pseudonymisation
de texte et de fichiers comptables, avec : UI PySide6, **Ollama** pour la détection floue,
relais Anthropic pour la pseudonymisation, parsing pandas/openpyxl, stockage DPAPI de la clé API.
Consigne : document d'inspiration, **pas** une spec à respecter — critique ouverte.

---

## Critique initiale (les risques relevés)

1. **Le détecteur le moins fiable portait la charge la plus sensible** : noms/adresses/orgs confiés
   à un LLM local (Ollama), alors que c'est là que le **rappel** est vital (un nom manqué = fuite).
2. **Offsets d'un LLM de chat peu fiables** (hallucination de positions, surtout en français accentué).
3. **Débit non traité** sur fichiers comptables volumineux (un appel LLM par cellule = des heures).
4. **Round-trip des tokens à travers Claude** (pseudonymisation) sous-spécifié et fragile.
5. **pandas ne préserve pas la mise en forme xlsx** (styles, formules, formats).
6. **« Anonymisation non réversible » + rapport d'audit** = contradiction (le rapport est une table
   de ré-identification).
7. **Aucune mesure de qualité** (pas de corpus d'éval, pas de plancher de rappel).
8. **LOGIN/PASSWORD** non détectables de façon fiable (pas de signature syntaxique).
9. **Pas de correction humaine** dans le flux (outil irréversible et faillible).

---

## Décisions, dans l'ordre

### D1 — Moteur de détection floue : **GLiNER** (pas Ollama)
Comparé Ollama vs NER spécialisés open source.
- **NER** = Named Entity Recognition : repérer + classer les entités (Personne/Lieu/Org).
- Candidats : **spaCy** (PERSON/LOC/ORG figés), **GLiNER** (labels libres, multilingue, spans
  fiables), **Presidio** (framework PII Microsoft = détection + transformation + réversible).
- Exemple décisif (texte FR avec adresse) : spaCy/Presidio ne taggent que la **ville**, ratent
  « 14 rue des Acacias » ; **GLiNER** capture le **span d'adresse complet** via un label libre.
- **Choix : A** — GLiNER pour le flou + couche déterministe maison + vault maison, en **réempruntant
  à Presidio** ses bonnes idées (résolution de chevauchements, dédup batch) **sans embarquer** le
  framework. Hypothèse C (Presidio orchestrateur + GLiNER dedans) écartée pour la v1 (poids/complexité).

### D2 — **Suppression totale d'Ollama**
GLiNER ne servait qu'à la détection floue → Ollama disparaît entièrement : plus de prérequis
d'install, plus d'écran de guidage, plus de JSON LLM fragile. App autonome côté détection.

### D3 — Périmètre v1 : **anonymisation seule** (texte + fichier)
Tranche minimale transverse (option C). Conséquence : **pas de vault, pas de tokens, pas de
round-trip Claude** en v1. Pseudonymisation + relais Anthropic + DPAPI → v2.

### D4 — **Revue humaine interactive** avant masquage (option A)
Écran de revue avec **codes couleurs par type d'entité**. L'utilisateur décoche ce qu'il ne faut
pas masquer, sélectionne du texte manqué pour l'ajouter. La légende de type sert de filtre global.
Couleurs fonctionnelles = jeu **fixe**, indépendant du thème (préserver le repère couleur=type).

### D5 — Mode fichier : sélection de colonnes = **option D**
Par défaut tout le texte sauf colonnes numériques/dates (règle A) **+** l'utilisateur peut
inclure/exclure des colonnes dans l'aperçu.

### D6 — **Rapport d'audit dans la v1** (option A)
Cheap une fois la détection faite, renforce la confiance. Avertissement « contient des valeurs
sensibles » ; pas d'inclusion par défaut dans des envois externes.

### D7 — Identité visuelle : **deux thèmes commutables**
Parcours : bleu/orange pastel → puis bleus de la charte **CAP Consulting** → puis verts **CUMA**.
L'utilisateur a tranché : **les deux**, commutables dans Paramètres.
- **Police de titres : A — Space Grotesk** (texte : Inter).
- Thème **CAP** = bleu `#1DA8E2` + orange `#E8621A` d'accent.
- Thème **CUMA** = verts CUMA, **sans orange** (accent = vert lime `#93C90E`).
- **Défaut au 1er lancement : CUMA (vert)** (option B).
- Gouvernance : ne pas mélanger les univers CAP / France Cuma Numérique ; le thème suit l'entité.

### D8 — PDF : **piste pour version ultérieure**, pas v1
Module dédié (caviardage pour PDF natif, OCR pour PDF scanné), pas une extension du moteur actuel.

### D9 — Nom de l'application : **Anonymator**

---

## Leçons des fichiers réels fournis

Deux fichiers : un **FEC** (`616870200FEC20231231.csv`) et un **grand livre** (`ccfbasc2.csv`).
1. **Séparateurs différents** : FEC en `|`, grand livre en `;` → **sniffing** obligatoire.
2. **Encodage Latin-1 / cp1252** (pas UTF-8) → détecter à la lecture, **réécrire à l'identique**.
3. **PII concentrée** dans peu de colonnes : `CompAuxLib` (nom du tiers), `EcritureLib` (libellé
   libre). Les `CompteLib` sont surtout génériques.
4. **Forte répétition** des valeurs → la **dédup batch** transforme des milliers de cellules en
   quelques centaines de valeurs uniques (gain massif, validé sur données réelles).
5. **Préserver le formatage** des cellules non masquées (espaces de cadrage, virgule décimale)
   → édition **en place** via openpyxl, jamais de round-trip pandas.
6. Beaucoup de contenu n'est **pas** de la PII (libellés comptables) → précision importante ;
   la revue + le toggle par type évitent de masquer p.ex. « Crédit Agricole ».

---

## Méthode

- Brainstorming guidé, une décision à la fois, avec compagnon visuel (maquettes navigateur) pour
  l'écran de revue couleur et les chartes graphiques.
- Suite prévue : **plan d'implémentation** (skill writing-plans), puis développement en **TDD**
  (checksums, fusion, substitution) avec corpus d'éval issu des fichiers réels.
