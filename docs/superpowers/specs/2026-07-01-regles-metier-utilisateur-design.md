# Règles métier utilisateur — Design

**Date** : 2026-07-01
**Statut** : validé (brainstorming), en attente de relecture avant plan d'implémentation

## Problème

La détection produit des **faux positifs** que l'utilisateur ne peut corriger qu'au cas par cas :

- Le modèle GLiNER (NER) classe des **codifications internes** comme des adresses/organisations : `A0000015`, `A0000020`, … (lettre + 7 chiffres), `A.N. au`, `71800 BOR03`. La `ner_stoplist` existante ne sait exclure que des **valeurs exactes** — inutilisable face à une famille de codes.
- L'heuristique d'entropie de `secrets_detect.py` masque **tout** token ≥ 8 caractères ayant ≥ 3 classes de caractères, **sans contexte**. Les conventions de nommage type `FACT.01/01/2023` sont donc prises pour des mots de passe.

Besoin exprimé : permettre à l'utilisateur de définir ses **propres règles métier**, à base de **motifs** (pas de valeurs exactes), **sans toucher au code**, et **partageables** avec un collègue.

## Objectifs

1. Un moteur de règles utilisateur **symétrique** :
   - `keep` (allow-list) : ne **jamais** masquer une valeur correspondant au motif ;
   - `mask` (force-list) : **toujours** masquer une valeur correspondant au motif, sous l'étiquette **`[REGLE-INTERNE]`**.
2. Motifs exprimés en **deux modes** au choix : **simple** (jokers) ou **expert** (regex brut).
3. **Assainir** l'heuristique PASSWORD pour supprimer la cause racine de la sur-détection.
4. **Fusionner** l'ancienne `ner_stoplist` dans ce nouveau système (un seul concept « Règles métier »).
5. Règles **stockées dans un fichier utilisateur**, dont le **chemin est affiché** dans l'interface, pour partage par simple copie.

## Non-objectifs (YAGNI)

- Pas de DSL générique conditions/actions.
- Pas d'étiquettes personnalisées multiples pour le forçage : **une seule** étiquette `[REGLE-INTERNE]`.
- Pas de portée par-catégorie : l'allow-list est **globale** (dernier mot sur tous les détecteurs).
- Pas (dans cette itération) de création de règle depuis l'écran de revue — noté comme piste future.

## Architecture

On réutilise le patron existant (celui de la `ner_stoplist`) : la force-list est un **détecteur** de plus, l'allow-list un **filtre** appliqué après fusion. Deux points d'insertion dans `pipeline.detect()` :

```
deterministic + secrets + ner + detect_forced(text, rules)   →  merge_entities  →  apply_allow(entities, rules)
```

Le moteur ne connaît qu'**une seule mécanique** : une **regex ancrée en fullmatch, insensible à la casse et aux accents**. Le mode `simple` est traduit en regex ; le mode `expert` fournit la regex directement.

### Module `anonymator/user_rules.py`

Classe `UserRules`, chargée depuis un fichier JSON (à l'image de `Referential`).

Structure d'une règle :

```json
{
  "mode": "simple",
  "pattern": "A#######",
  "action": "keep",
  "enabled": true,
  "note": "codification interne"
}
```

- `mode` : `"simple"` | `"regex"`.
- `pattern` : motif tel que saisi par l'utilisateur.
- `action` : `"keep"` (ne jamais masquer) | `"mask"` (toujours masquer → `[REGLE-INTERNE]`).
- `enabled` : booléen (désactiver sans supprimer).
- `note` : libellé libre pour s'y retrouver.

Le champ étiquette est **absent** : toute règle `mask` masque sous `[REGLE-INTERNE]`.

**Traduction simple → regex** (fonction `compile_pattern`) :

| Joker (mode simple) | Regex |
|---|---|
| `#` | `\d` (un chiffre) |
| `?` | `.` (un caractère quelconque) |
| `*` | `.*` (n'importe quelle suite, éventuellement vide) |
| tout autre caractère | échappé littéralement (`re.escape`) |

- La regex finale est ancrée : `re.fullmatch`, options `re.IGNORECASE`.
- Insensibilité aux accents : la comparaison se fait sur la valeur **normalisée** via `textnorm.normalize`, appliquée de la même façon au motif et à la valeur testée. (Détail d'implémentation à confirmer au plan : normaliser le texte avant match, ou intégrer une équivalence accent dans la regex. Choix par défaut : normaliser des deux côtés, cohérent avec la stoplist actuelle.)
- Une regex invalide (mode expert) est **ignorée** (règle inerte) et signalée dans l'UI ; elle ne fait jamais planter la détection.

### Intégration pipeline (`anonymator/pipeline.py`)

- `detect_forced(text, rules) -> list[Entity]` : pour chaque règle `action="mask"` activée, chaque `re.finditer` sur le texte produit un `Entity(type="REGLE_INTERNE", value, start, end, source="rule", confidence=1.0)`. Ajouté au tas **avant** `merge_entities`.
- `apply_allow(entities, rules) -> list[Entity]` : **après** `merge_entities`, retire toute entité dont la **valeur** correspond (fullmatch normalisé) à une règle `action="keep"` activée.

`detect()` devient :

```python
forced = detect_forced(text, rules)
merged = merge_entities(deterministic + secrets + ner_entities + forced)
return apply_allow(merged, rules)
```

### Précédence

`keep` a le **dernier mot** : `apply_allow` s'exécutant après tout le reste, une valeur correspondant à la fois à une règle `keep` et `mask` (ou détectée par ailleurs) est **conservée en clair**. C'est la protection anti-sur-masquage voulue.

### Priorité de fusion des entités forcées

`merge.py::_rank` privilégie aujourd'hui `source == "deterministic"`. Pour qu'une entité forcée gagne un chevauchement contre le NER, on étend `_rank` afin de traiter `source in ("deterministic", "rule")` comme prioritaire. (Peu importe qui gagne au final si `apply_allow` retire ensuite l'entité ; mais une entité forcée doit survivre à la fusion pour être effectivement masquée.)

### Étiquette `[REGLE-INTERNE]`

Ajout dans `anonymator/config/entities.json` d'une entrée :

```json
{"code": "REGLE_INTERNE", "label": "Règle interne", "method": "rule",
 "active": true, "tag": "[REGLE-INTERNE]", "sensitivity": "Moyenne"}
```

Ainsi `Referential.tag_for("REGLE_INTERNE")` renvoie `[REGLE-INTERNE]` et le rapport d'audit sait l'afficher. La méthode `"rule"` la distingue des types NER/déterministes dans l'UI des types (elle n'apparaît pas comme un type activable/désactivable classique — à cadrer au plan).

## Assainissement de l'heuristique PASSWORD

Dans `anonymator/secrets_detect.py`, `_looks_like_secret` ne déclenche plus l'entropie que sur une **vraie signature de secret** :

- Condition renforcée : présence simultanée de **minuscules ET majuscules ET chiffres** (un secret « fort »).
  - Rationnel : les conventions de nommage (`FACT.01/01/2023`, `BOR03`, `A0000015`) sont en **majuscules + chiffres + ponctuation, sans minuscule** → elles cessent d'être détectées.
  - Un vrai mot de passe faible tout en minuscules+chiffres sans contexte pourrait passer sous le radar : accepté (arbitrage validé), d'autant que l'allow-list/force-list et le chemin « mot-clé de contexte » restent disponibles.
- Le chemin **contextuel** (`_PWD_RE` / `_LOGIN_RE`, déclenché par « mot de passe : … », « mdp », « login … ») est **inchangé** : fiable, on n'y touche pas.

Tests de non-régression : `FACT.01/01/2023`, `A0000015`, `BOR03` ne sont plus `PASSWORD` par entropie ; un token type `Xk9$mPq2a` (min+maj+chiffre+symbole) l'est toujours ; `mot de passe : abc123` reste détecté par le chemin contextuel.

## Fusion de la `ner_stoplist`

- Les termes de la stoplist (`config/ner_stoplist.json` + `preferences.ner_stoplist`) sont **migrés** en règles `{mode:"simple", pattern:<terme>, action:"keep", enabled:true, note:"importé de la liste d'exclusion"}`.
- La migration s'exécute une fois, au chargement, si `user_rules.json` n'existe pas encore et qu'une ancienne stoplist est présente.
- Comportement préservé : la stoplist matchait en normalisé et **uniquement** le NER ; les règles `keep` matchent en normalisé mais **globalement**. L'élargissement est intentionnel (un terme qu'on ne veut jamais masquer, on ne veut jamais le masquer, quelle que soit sa source).
- L'ancien éditeur « Liste d'exclusion (NER) » de `settings_screen.py` est **remplacé** par l'éditeur de règles. Le champ `Preferences.ner_stoplist` est conservé en lecture pour la migration, puis n'est plus alimenté.

## Interface (`anonymator/ui/settings_screen.py`)

Nouvelle section **« Règles métier »**, dans la veine de l'éditeur de stoplist actuel :

- **Liste des règles** : chaque ligne montre `note` (ou le motif), le mode, l'action (`garder` / `masquer`), un interrupteur `enabled`, un bouton supprimer.
- **Ajout d'une règle** : champ motif + sélecteur **Simple / Expert** + sélecteur **Ne jamais masquer / Toujours masquer** + champ note. (Pas de champ étiquette : `mask` ⇒ `[REGLE-INTERNE]`.)
- **Validation** en saisie : en mode expert, une regex invalide est signalée (message) et la règle n'est pas enregistrable tant qu'elle est invalide.
- **Chemin du fichier** : un libellé affiche le chemin complet de `user_rules.json` (ex. `C:\Users\<nom>\.anonymator\user_rules.json`) + un bouton **« Ouvrir le dossier »**, pour retrouver et partager le fichier.

## Stockage (`anonymator/ui/preferences.py` / nouveau chargeur)

- Fichier dédié : `Path.home() / ".anonymator" / "user_rules.json"` (à côté de `preferences.json`).
- Format : `{ "rules": [ …, … ] }`.
- Chargé au démarrage (comme la stoplist), éditable à la main, **partageable** par copie.
- Absence de fichier ⇒ liste vide (après migration éventuelle de la stoplist).

## Découpage en unités (isolation)

- `compile_pattern(mode, pattern) -> re.Pattern` : pure, testable seule (traduction jokers + ancrage + flags).
- `UserRules` : chargement/sauvegarde JSON, exposition des règles `keep` / `mask` compilées.
- `detect_forced(text, rules)` : pure (texte + règles → entités).
- `apply_allow(entities, rules)` : pure (entités + règles → entités filtrées).
- `secrets_detect._looks_like_secret` : modification locale, couverte par tests existants + nouveaux.
- UI : section additionnelle isolée dans `settings_screen.py`.

## Plan de tests

- **`compile_pattern`** : `#`→chiffre, `*`→`.*`, `?`→un caractère, échappement de `.` et `/`, insensibilité casse/accents, ancrage fullmatch. `A#######` matche `A0000015` mais pas `A000001` ni `XA0000015X`. `FACT.*` matche `FACT.01/01/2023`. Regex expert invalide → règle inerte.
- **`detect_forced`** : émet une entité `REGLE_INTERNE` par occurrence ; survit à la fusion contre un NER chevauchant.
- **`apply_allow`** : retire les entités dont la valeur matche une règle `keep` ; laisse les autres ; `enabled:false` sans effet.
- **Précédence** : valeur matchant `keep` et `mask` → conservée en clair.
- **PASSWORD** : non-régression décrite plus haut.
- **Migration stoplist** : termes existants convertis en règles `keep` équivalentes ; comportement de masquage inchangé sur un texte de référence.
- **Persistance** : `user_rules.json` écrit/relu ; absence de fichier → liste vide.
- **UI smoke** : la section se construit, ajoute/supprime une règle, affiche le chemin.

## Points ouverts (à trancher au plan)

1. Normalisation accents : normaliser des deux côtés (défaut retenu) vs. équivalence dans la regex.
2. Exposition de `REGLE_INTERNE` dans la liste des types d'entités (le rendre visible en lecture seule, ou l'exclure de cette liste).
3. « Ouvrir le dossier » : commande d'ouverture de l'explorateur portable (Windows cible principale).
