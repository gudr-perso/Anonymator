# Expérience GLiNER « zéro friction » — Doc de conception

> Refonte du parcours d'installation et d'utilisation du modèle de détection **GLiNER**, pour le
> rendre le plus simple possible côté utilisateur.
> Brainstorming du 2026-06-30. Complète [2026-06-29-anonymator-design.md](2026-06-29-anonymator-design.md)
> §2 (packaging, modèle découplé) et §9 (modèle absent → guidage).

---

## 1. Contexte & problème

GLiNER (détection floue des **noms / adresses / organisations**) tire PyTorch + transformers et
nécessite le téléchargement d'un modèle (~300 Mo) au premier usage, mis en cache dans le dossier
utilisateur (`~/.cache/huggingface`, hors pCloud).

L'état actuel impose un **écran de configuration bloquant** au premier lancement
([`setup_screen.py`](../../../anonymator/ui/setup_screen.py)) : l'utilisateur ne peut rien faire tant
que le modèle n'est pas téléchargé, la progression est une animation **indéterminée** accompagnée
d'un log technique, et **aucun écran** ne permet ensuite de consulter l'état du modèle ou de le
re-télécharger.

Nuance clé : **seuls** les noms / adresses / organisations passent par GLiNER. Tout le reste (IBAN,
e-mail, téléphone, SIREN/SIRET, NIR, mots de passe…) est détecté par des **règles déterministes qui
ne nécessitent aucun modèle**. Le logiciel a donc une valeur réelle même sans GLiNER.

---

## 2. Principe directeur

Le logiciel est **toujours utilisable immédiatement**. GLiNER est un *bonus* qui s'installe en un
clic, **jamais un prérequis**. Aucun écran bloquant.

---

## 3. Décisions verrouillées

1. **Premier lancement non bloquant** : l'app ouvre directement sur l'accueil. Une **carte d'invite**
   propose le téléchargement si le modèle est absent.
2. **Gestion du modèle dans Paramètres** : une section permanente « Modèle de détection » (statut,
   emplacement, bouton télécharger/réparer, explication, barre de progression).
3. **Barre de progression réelle** (% + Mo) pendant le téléchargement, pilotée par un callback
   `huggingface_hub`.
4. **Mode dégradé** : sans modèle, la détection tourne en **déterministe seul** et signale clairement
   que noms / adresses / organisations ne sont pas détectés, avec un lien pour installer.
5. Une fois le modèle installé (depuis l'accueil ou Paramètres), la détection complète **reprend sans
   redémarrer**.
6. L'écran de setup bloquant actuel est **supprimé**.

---

## 4. Flux utilisateur

### 4.1 Premier lancement (modèle absent)
- L'app ouvre directement sur l'**accueil**.
- L'accueil affiche une **carte d'invite** (style visuel V1/V2 existant) :
  > « 🧠 Détection intelligente des noms, adresses et organisations — téléchargement unique
  > (~300 Mo). Les détections par règles (IBAN, e-mail, téléphone, mots de passe…) fonctionnent déjà
  > sans elle. »
  > **[ Télécharger maintenant ]**   **[ Plus tard ]**
- « Plus tard » masque la carte **pour la session courante**. Elle réapparaît au prochain lancement
  tant que le modèle n'est pas installé. Le téléchargement reste toujours accessible via Paramètres.
- Si le modèle est **présent**, la carte n'apparaît pas.

### 4.2 Lancer une détection sans modèle (mode dégradé)
- Avant chaque analyse, l'app vérifie `is_model_available()`.
- **Modèle présent** → détection complète (déterministe + GLiNER chargé depuis le cache).
- **Modèle absent** → détection **déterministe seule** via `NullNer` (ne télécharge rien, ne plante
  pas). Le résultat affiche un **bandeau** :
  > « ⚠️ Noms / adresses / organisations non détectés (modèle non installé).
  > **[ Installer maintenant ]** »
- Le bandeau dégradé concerne les écrans Texte **et** Fichier.

### 4.3 Téléchargement
- Déclenchable depuis la carte d'invite (accueil) **ou** la section Paramètres.
- Pendant le téléchargement : barre **réelle** (% + Mo, ex. « 142 / 300 Mo — 47 % »), boutons de
  déclenchement désactivés, message d'état.
- À la fin : statut passe à « Installé », la carte d'invite disparaît, les bandeaux dégradés
  disparaissent, la détection complète est disponible **sans redémarrage**.
- En cas d'erreur (réseau…) : message clair, bouton réactivé pour réessayer.

---

## 5. Architecture des modules

Principe inchangé du projet : **la logique vit hors de Qt**, testable isolément ; les widgets Qt sont
des vues minces.

### 5.1 Cœur (non-Qt)

- **`anonymator/ner.py`** — ajout de `NullNer` : implémente le protocole `NerDetector`,
  `detect(text, labels)` retourne `[]`. Sert le mode dégradé sans charger torch ni rien télécharger.

- **`anonymator/core/model_status.py`** — déjà : `is_model_available()`, `model_cache_dir()`.
  Ajout : `installed_size() -> int | None` (octets sur disque du cache modèle, `None` si absent) pour
  afficher la taille dans Paramètres.

### 5.2 Téléchargement avec progression

- **`anonymator/ui/download_worker.py`** (`QThread`, réécrit) — signaux :
  - `progress(received: int, total: int)` — octets cumulés / total.
  - `status(str)` — étape lisible (« Connexion… », « Téléchargement… », « Finalisation… »).
  - `download_finished()` / `error(str)`.
  - Implémentation : déterminer la **taille totale** du dépôt via `huggingface_hub`
    (`HfApi().model_info(...).siblings` ou équivalent), puis télécharger
    (`snapshot_download`) en cumulant les octets reçus via un callback / `tqdm_class` custom qui émet
    `progress`. Si le total ne peut être déterminé, la barre repasse en indéterminée (dégradation
    silencieuse, non visible comme fonctionnalité).

### 5.3 Vues Qt (minces)

- **`anonymator/ui/settings_screen.py`** — nouvelle section « Modèle de détection » :
  statut (installé + taille / non installé), emplacement du cache, bouton **Télécharger** /
  **Réparer (re-télécharger)**, barre de progression, texte d'explication du process. Réutilise les
  composants V1 (`Card`, etc.) dans la mesure du possible.

- **`anonymator/ui/home_screen.py`** — **carte d'invite** affichée si modèle absent, avec
  « Télécharger maintenant » et « Plus tard ». Masquable pour la session ; pilotée par l'état fourni
  par `MainWindow`.

- **`anonymator/ui/text_screen.py`** / **`anonymator/ui/file_screen.py`** — au moment d'analyser,
  choisir le détecteur : `loader.get()` (GLiNER) si modèle présent, sinon `NullNer`. Afficher le
  **bandeau dégradé** quand `NullNer` est utilisé, avec action « Installer maintenant ».

- **`anonymator/ui/main_window.py`** — orchestration :
  - entrée **non bloquante** (toujours `show_home()` au démarrage ; plus de bascule vers le setup) ;
  - centralise le déclenchement du téléchargement et diffuse « modèle prêt » pour rafraîchir accueil,
    Paramètres et écrans (la carte d'invite et les bandeaux disparaissent, la détection complète
    devient disponible) ;
  - garantit qu'un seul téléchargement tourne à la fois.

- **`anonymator/ui/setup_screen.py`** — **supprimé** ; sa logique de téléchargement est reprise par
  `download_worker.py` + la section Paramètres + la carte d'invite. Le paramètre `skip_setup` de
  `MainWindow` et les tests associés sont nettoyés en conséquence.

---

## 6. Modèle de décision détecteur

| État du modèle | Détecteur utilisé | Détection noms/adr/org | Détection règles | Bandeau dégradé |
| --- | --- | --- | --- | --- |
| Présent | `GlinerDetector` (cache) | ✅ | ✅ | non |
| Absent | `NullNer` | ❌ | ✅ | oui |

La sélection se fait à chaque analyse selon `is_model_available()` — un téléchargement réussi en
cours de session fait donc basculer automatiquement vers `GlinerDetector` à l'analyse suivante.

---

## 7. Gestion des erreurs & cas limites

- **Pas de réseau / téléchargement échoue** : `error(msg)` → message clair dans la section/​carte,
  bouton réactivé pour réessayer ; l'app reste utilisable en mode dégradé.
- **Téléchargement déjà en cours** : les boutons (accueil + Paramètres) sont désactivés ; pas de
  second worker.
- **Total de taille indéterminable** : barre indéterminée en repli (le téléchargement aboutit quand
  même).
- **Fermeture pendant le téléchargement** : le worker est arrêté proprement (`quit()` + `wait()`),
  comme l'actuel `closeEvent`.
- **Modèle partiellement téléchargé / corrompu** : « Réparer » relance un `snapshot_download`
  (HuggingFace complète/retélécharge les fichiers manquants).

---

## 8. Tests (TDD)

### Cœur (sans Qt, sans torch)
- `test_ner.py` (ou existant) : `NullNer().detect(...)` retourne `[]`.
- `test_model_status.py` (étendu) : `installed_size()` → `None` si absent, somme des fichiers si
  présent (cache simulé via `tmp_path`).

### Vue Qt (pytest-qt, offscreen, sans vrai téléchargement)
- `test_settings_screen.py` (étendu) : la section « Modèle de détection » montre le bon statut selon
  `is_model_available` (patché) ; cliquer « Télécharger » démarre le worker (worker patché/factice).
- `test_home_screen.py` : carte d'invite présente si modèle absent, absente sinon ; « Plus tard » la
  masque.
- `test_text_screen.py` / `test_file_screen.py` (étendus) : sans modèle → `NullNer` utilisé, bandeau
  dégradé visible, détections déterministes toujours présentes ; avec modèle (FakeNer injecté) → pas
  de bandeau.
- `test_ui_smoke.py` (étendu) : l'app démarre **toujours** sur l'accueil (plus de setup bloquant),
  modèle présent ou absent.
- `test_download_worker.py` (nouveau, sans réseau réel) : émission des signaux `progress` agrégés à
  partir d'un téléchargement simulé (callback/​tqdm factice).

### Validation manuelle « à l'identique de l'utilisateur »
Sur cette machine (vierge de modèle), via **`dist/anonymator/anonymator.exe`** uniquement (jamais le
venv de dev) :
1. Lancement → accueil direct + carte d'invite.
2. Analyse en mode dégradé d'un texte avec IBAN + nom → IBAN masqué, nom non masqué, bandeau dégradé
   affiché.
3. Clic « Télécharger » → barre % progresse jusqu'à 100 %.
4. Nouvelle analyse → nom détecté, plus de bandeau ; carte d'invite disparue ; Paramètres affiche
   « Installé » + taille.

---

## 9. Hors périmètre

- Choix du modèle GLiNER / multi-modèles, calibrage du seuil (`threshold`) ou des labels.
- Téléchargement en arrière-plan automatique sans action utilisateur.
- Mise à jour / versionnage du modèle, vérification d'intégrité par hash.
- Installeur Windows, code signing (Plan 5 éventuel).

---

## 10. Décisions verrouillées (récapitulatif)

1. Premier lancement **non bloquant** ; carte d'invite sur l'accueil si modèle absent.
2. Gestion du modèle dans une **section Paramètres** dédiée.
3. **Barre de progression réelle** (% + Mo) via callback `huggingface_hub`.
4. **Mode dégradé** (déterministe seul + bandeau) quand le modèle est absent ; reprise automatique
   après installation, sans redémarrage.
5. `NullNer` (cœur) pilote le mode dégradé ; `setup_screen.py` supprimé.
6. Validation finale via l'exe packagé, à l'identique de l'utilisateur.
