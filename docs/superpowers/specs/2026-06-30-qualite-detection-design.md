# Qualité de détection — Doc de conception

> Amélioration du **rappel** et de la **précision** du moteur de détection PII (modes Texte et Fichier).
> Brainstorming du 2026-06-30. Complète [2026-06-29-anonymator-design.md](2026-06-29-anonymator-design.md) §4
> et s'articule avec [2026-06-30-revue-fichier-coloree-design.md](2026-06-30-revue-fichier-coloree-design.md).

---

## 1. Contexte & problème

Un cas de test réel (paragraphe riche en PII) a révélé des manques sérieux du moteur, **transverses**
aux modes Texte et Fichier :

| Attendu | Détecté ? | Cause racine |
| --- | --- | --- |
| BIC, Code postal | ❌ | `active: false` dans `entities.json` — jamais cherchés |
| IBAN, N° sécu (valeurs de test) | ❌ | format OK mais **checksum/clé invalide** → rejetés |
| Logins, mots de passe | ❌ | **aucune catégorie** |
| « service client » → ORG | faux positif | sur-détection GLiNER |

Ce spec corrige ces quatre points. Les noms, adresses, e-mails et téléphones étaient correctement
détectés ; on n'y touche pas.

**Principe directeur conservé** : « le détecteur propose, le code dispose ». Les validations
déterministes (mod 97, Luhn, clé NIR) restent la référence ; on ajoute un statut explicite pour les
valeurs **format-plausibles mais non validées**, plutôt que de les masquer aveuglément.

---

## 2. Décisions verrouillées

1. **BIC / Code postal / URL** : pas forcés. **Options activables** par l'utilisateur dans les
   Paramètres, **désactivées par défaut**.
2. **IBAN / NIR au format plausible mais clé invalide** : **non masqués par défaut**, **signalés**
   « non confirmé », **masquables au choix** dans la revue.
3. **Logins & mots de passe** : nouvelles catégories, détectées par **règles contextuelles +
   heuristique d'entropie** (cadrée).
4. **Faux positifs GLiNER** : **liste d'exclusion** éditable de termes génériques.

---

## 3. Modèle d'entité & nouvelles catégories

- **`Entity` gagne `confirmed: bool` (défaut `True`).** Une détection déterministe dont seul le
  **format** est valide (checksum/clé KO) porte `confirmed=False`. Le **type** reste inchangé
  (`IBAN`, `NIR`) → une seule couleur/catégorie ; le statut « non confirmé » est un attribut
  transversal exploité par la revue, le rapport et le masquage.
  - *Alternative écartée* : surcharger `confidence` (probabilité GLiNER). `confirmed` (validation
    déterministe) et `confidence` (score NER) sont deux notions distinctes.
- **Deux nouveaux types** :
  - `LOGIN` → tag `[LOGIN]`, sensibilité **Haute**, actif & masqué par défaut.
  - `PASSWORD` → tag `[SECRET]`, sensibilité **Haute**, actif & masqué par défaut.
  - Couleurs dédiées dans [`colors.py`](../../../anonymator/ui/colors.py).

---

## 4. Détection logins / mots de passe — `anonymator/secrets_detect.py` (nouveau)

**4.1 Règles contextuelles** (base fiable, déterministe) : un mot-clé déclencheur capture le jeton voisin.
- Mot de passe : `(?:mot de passe|mdp|password|pass(?:e)?)(?:\s+(?:provisoire|temporaire))?` → jeton
  suivant (après séparateurs `:`, `—`, `(`, espaces).
- Login : `(?:login|identifiant|utilisateur|user(?:name)?|accès au compte|connect[ée]\w*\s+avec)` →
  jeton voisin.
- « Jeton » = séquence sans espace, bornée par ponctuation de fin de phrase / parenthèse fermante.

**4.2 Heuristique d'entropie** (secrets sans contexte), **strictement cadrée** :
- ≥ 3 classes parmi {minuscule, majuscule, chiffre, symbole}, longueur ≥ 8 ;
- exclut les jetons purement numériques ou structurés, et ceux déjà typés par une autre règle
  (IBAN, BIC, SIREN/SIRET, NIR, n° de compte) ;
- en mode **Fichier**, ne s'applique qu'aux **colonnes masquables** (texte libre), jamais aux
  colonnes numériques.

Les deux sources produisent des `Entity` `LOGIN`/`PASSWORD` et passent par la fusion existante
(`merge_entities`). Détection intégrée à `pipeline.detect` au même titre que `detect_deterministic`.

---

## 5. IBAN / NIR « non confirmés »

- Dans [`deterministic.py`](../../../anonymator/deterministic.py), **pour IBAN et NIR uniquement** : si
  le format correspond mais que le validateur échoue, émettre l'`Entity` avec `confirmed=False` (au
  lieu de la jeter). BIC, SIREN, SIRET, Code postal gardent « rejet si invalide ».
- **Masquage par défaut** : une entité `confirmed=False` n'est **pas** masquée — voie directe comme
  revue.
- **Revue** (texte & fichier) : surlignage distinct (hachuré/atténué) + badge « non confirmé », case
  **décochée** ; l'utilisateur peut cocher pour masquer. Libellé : « format valide mais clé de
  contrôle invalide — probablement une valeur factice ou une coquille ».
- **Rapport d'audit** : indicateur `confirmé` (oui/non) par entrée masquée.

---

## 6. Faux positifs GLiNER — liste d'exclusion

- Fichier par défaut **`anonymator/config/ner_stoplist.json`** : termes génériques à ne jamais retenir
  comme entité NER (« service client », « client », « fournisseur », « divers », « la société », …).
- **Filtrage dans `pipeline.detect`** : après GLiNER, retirer les entités dont la valeur normalisée
  (minuscule, accents retirés) figure dans la liste. N'affecte **que** les détections NER.
- Éditable dans les Paramètres (§7), persistée dans les préférences.

---

## 7. Écran Paramètres — éditeur de détection

Extension de [`settings_screen.py`](../../../anonymator/ui/settings_screen.py), zone « Détection » :

1. **Types d'entités (référentiel)** : liste de tous les types avec **case activé/désactivé** + libellé.
   C'est ici qu'on active **BIC / Code postal / URL** (off par défaut). Persistance via
   `preferences.entity_overrides` (**champ déjà existant**) ; `Referential.is_active` consulte ces
   surcharges.
2. **Liste d'exclusion GLiNER** : éditeur **liste** dédié — champ + bouton « Ajouter », et chaque ligne
   avec un bouton « ✕ » pour retirer (pas un bloc de texte brut).

**Stockage & défauts (compatibilité exe packagé)** : `config/` est en **lecture seule** dans l'exe ; les
éditions utilisateur vont dans `preferences.json` (dossier personnel, inscriptible). La liste
d'exclusion par défaut est livrée dans `config/ner_stoplist.json` ; au premier affichage l'écran la
charge, et dès modification la **liste effective complète** est écrite dans `preferences.json`. À
l'exécution, `pipeline.detect` utilise la liste des préférences si présente, sinon le défaut du config.

---

## 8. Intégration revue & masquage par défaut

- `LOGIN`, `PASSWORD` : actifs & masqués par défaut. `BIC`/`CP`/`URL` : inactifs jusqu'à activation.
- Entités `confirmed=False` : retenues = **non** par défaut partout ; opt-in dans la revue (§5).
- `ReviewSession` (texte) et `FileReviewSession` (fichier, spec précédent) traitent `confirmed` de
  façon identique (décoché par défaut, badge « non confirmé ») ; les nouveaux types apparaissent dans
  le panneau des typologies comme les autres.

---

## 9. Tests (TDD)

Cœur déterministe (sans Qt) :
- `test_validators.py` (étendu) : IBAN/NIR valides → `True` ; format-plausible-clé-fausse reconnus
  comme « format OK » (pilote `confirmed=False`).
- `test_deterministic.py` : IBAN/NIR format-correct-invalide → émis `confirmed=False` ; BIC/CP/URL
  émis si actifs ; types inactifs jamais émis.
- `test_secrets_detect.py` (nouveau) : règles contextuelles (« mot de passe — X », « accès au compte
  (Y) », « connectée avec Z ») → `PASSWORD`/`LOGIN` ; entropie sur `V3lo!2026#Claire` /
  `T0ulouse*Hugo-90` → `PASSWORD` ; **non-régression** : `41100000`, réf de pièce, montant ne
  déclenchent pas `PASSWORD`.
- `test_pipeline.py` : la liste d'exclusion retire « service client » mais pas une vraie personne ;
  n'affecte pas le déterministe.
- `test_referential.py` : `entity_overrides` activent/désactivent un type ; défauts (BIC/CP/URL off,
  LOGIN/PASSWORD on).
- `test_review_session.py` (étendu) : `confirmed=False` non retenue par défaut ; la cocher → masquée ;
  rapport trace le statut `confirmé`.

Vue Qt (pytest-qt, smoke) :
- `test_settings_screen.py` (étendu) : activer BIC → `prefs.entity_overrides["BIC"] is True` +
  `on_apply` appelé ; ajouter/retirer un terme d'exclusion met à jour et persiste la liste.

**Cas de bout en bout** (paragraphe de test fourni) : logins & mots de passe masqués ; IBAN/NIR
signalés « non confirmé » (masquables au choix) ; BIC/CP masqués **si** activés ; « service client »
non masqué grâce à la liste d'exclusion.

---

## 10. Périmètre & découpage

Ce spec touche : `model.py` (`confirmed`), `deterministic.py`, `secrets_detect.py` (nouveau),
`pipeline.py` (secrets + stoplist + confirmed), `referential.py` (overrides + stoplist), `entities.json`
(nouveaux types + défauts), `config/ner_stoplist.json` (nouveau), `colors.py`, `preferences.py`
(déjà `entity_overrides` ; ajout liste d'exclusion), `settings_screen.py`, `review_session.py`.

C'est volumineux : à l'étape **writing-plans**, prévoir un **découpage en 2-3 plans** cohérents
(ex. 1 : modèle + déterministe + secrets + pipeline ; 2 : référentiel + stoplist + Paramètres ;
3 : intégration revue `confirmed`), plutôt qu'un seul plan monolithique.
