# Installer et tester GLiNER (détection floue réelle)

> Marche à suivre pour activer **GLiNER** (le détecteur de noms / adresses / organisations) et lancer
> le test d'intégration. À faire **une seule fois**, délibérément, car l'installation est lourde.
> Tant que ce n'est pas fait, le cœur reste entièrement testable via `FakeNer` (43 tests unitaires verts).

---

## 1. Pourquoi c'est une étape à part

- `gliner` tire **PyTorch** + `transformers` + `huggingface_hub` : plusieurs centaines de Mo, install de quelques minutes.
- Le dossier projet est dans **pCloud (synchronisé)**. Installer PyTorch dans `.venv/` ici ferait synchroniser **plusieurs Go** par pCloud. `.gitignore` n'a aucun effet sur la synchro pCloud (mécanismes séparés).
- Le **modèle GLiNER** est mis en cache dans `~/.cache/huggingface` (dossier utilisateur, **hors pCloud**) → seul le `.venv` pose le problème de synchro.
- Tout le pipeline est prouvé sans PyTorch grâce à `FakeNer` ; le seul test qui exige le vrai modèle est marqué `@pytest.mark.integration` et **exclu par défaut**.

---

## 2. AVANT d'installer — neutraliser la synchro pCloud du venv

Choisir **une** des deux options.

### Option A (simple) — exclure `.venv/` de la synchro pCloud
1. Clic droit sur le dossier `C:\_pCloud\Extensions\anonymise\.venv`
   → menu pCloud → **« Exclure de la synchronisation »** (ou via pCloud Drive → Paramètres → Dossiers synchronisés).
2. Vérifier que `.venv` n'est plus dans la liste des dossiers synchronisés.

> Si le `.venv` n'existe pas encore, crée-le d'abord (voir §3 étape 1) puis exclus-le **avant** d'installer PyTorch.

### Option B (plus radicale) — venv HORS du dossier pCloud
Créer l'environnement ailleurs, p. ex. `C:\dev\anonymator-venv`, et l'utiliser à la place de `.venv` :
```bash
python -m venv C:/dev/anonymator-venv
```
Puis, dans les commandes ci-dessous, remplacer `.venv/Scripts/python` par `C:/dev/anonymator-venv/Scripts/python`.

---

## 3. Installation + test

> ⚠️ Sur cette machine, `python` / `python3` sont des **stubs Windows Store** non fonctionnels.
> Toujours passer par l'interpréteur du venv : `.venv/Scripts/python`.

Depuis `C:\_pCloud\Extensions\anonymise` :

```bash
# 1. (si pas déjà fait) créer le venv — puis l'EXCLURE de pCloud (§2) avant l'étape 2
python -m venv .venv

# 2. installer les dépendances lourdes (gliner + torch + transformers)
.venv/Scripts/python -m pip install -r requirements.txt

# 3. lancer le test d'intégration (télécharge le modèle au 1er run, dans ~/.cache/huggingface)
.venv/Scripts/python -m pytest -m integration -v
```

**Résultat attendu :** `test_gliner_detects_person_and_address` PASSED (le 1er run prend plusieurs minutes
le temps de télécharger le modèle ; les suivants sont rapides).

---

## 4. Vérification manuelle rapide (facultatif)

Pour voir GLiNER détecter en conditions réelles :
```bash
.venv/Scripts/python -c "from anonymator.ner import GlinerDetector; d=GlinerDetector(); print([(e.type,e.value) for e in d.detect('Jean-Pierre Lefevre habite 14 rue des Acacias a Toulouse, fournisseur SARL Bati-Sud.', ['personne','adresse postale','organisation'])])"
```

Et le pipeline complet (déterministe + GLiNER + masquage) :
```bash
.venv/Scripts/python -c "from anonymator.pipeline import detect; from anonymator.anonymize import apply_masking; from anonymator.referential import Referential; from anonymator.ner import GlinerDetector; ref=Referential.load_default(); ner=GlinerDetector(); t='Le client Jean-Pierre Lefevre, IBAN FR76 3000 6000 0112 3456 7890 189.'; print(apply_masking(t, detect(t, ner, ref), ref))"
```

---

## 5. Lancer toute la suite, intégration comprise

Par défaut le marqueur `integration` est exclu (`addopts = -m 'not integration'` dans `pyproject.toml`).
Pour tout lancer :
```bash
.venv/Scripts/python -m pytest -m "integration or not integration" -v
```

---

## 6. Dépannage

| Symptôme | Cause probable | Action |
|---|---|---|
| pCloud upload des Go après l'install | `.venv` resté synchronisé | Refaire §2 (exclure `.venv`) ; envisager l'option B |
| `python` ouvre le Microsoft Store / ne fait rien | stub Windows Store | utiliser `.venv/Scripts/python` (jamais `python` nu) |
| Téléchargement du modèle très lent / échoue | réseau ou cache HF | relancer ; le cache est dans `~/.cache/huggingface` |
| `ModuleNotFoundError: gliner` au test d'intégration | dépendances non installées | refaire §3 étape 2 |
| Rappel d'adresses faible | seuil/labels GLiNER à calibrer | ajuster `threshold` / les labels dans `anonymator/ner.py` (étape de calibrage, hors test) |

---

*Rappel : ne JAMAIS committer `.venv/` (déjà couvert par `.gitignore`). Le modèle GLiNER n'est pas embarqué dans le dépôt ni dans l'exe — il est téléchargé/caché localement au 1er usage.*
