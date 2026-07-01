# Licences des composants tiers embarqués

Anonymator lui-même est distribué sous **AGPL-3.0** (voir le fichier `LICENSE` à la
racine). L'exécutable distribué (build PyInstaller) embarque en plus des bibliothèques
tierces, chacune sous sa propre licence. Ce dossier regroupe les notices requises.

> ⚠️ Ceci décrit la mécanique des licences ; ce n'est pas un avis juridique.

## Composant sous copyleft — obligations de redistribution

### Qt / PySide6 — LGPL-3.0

L'interface graphique utilise **PySide6**, les liaisons Python officielles de **Qt**
(© The Qt Company), distribuées sous **GNU LGPL-3.0** (texte complet :
[`LGPL-3.0.txt`](LGPL-3.0.txt), qui étend la [`GPL-3.0.txt`](GPL-3.0.txt)).

La LGPL exige que l'utilisateur puisse **remplacer / re-linker** la bibliothèque Qt par
une version modifiée. Cette liberté est satisfaite ici de deux façons :

- Le build est un **paquet « onedir »** : les bibliothèques Qt (`.dll` / `.pyd`) sont des
  fichiers séparés dans le dossier distribué et peuvent être remplacés par l'utilisateur.
- Le **code source complet** d'Anonymator est public sous AGPL-3.0
  (<https://github.com/gudr-perso/Anonymator>) : l'utilisateur dispose des instructions
  de build et peut recompiler l'application avec sa propre version de Qt.

AGPL-3.0 (code de l'application) et LGPL-3.0 (Qt) sont **compatibles** (licences GNU v3).

## Composants sous licences permissives

Ces bibliothèques sont embarquées sous des licences permissives (attribution) ; leur
texte de licence complet est fourni dans le dossier `*.dist-info` de chaque paquet au
sein de l'arbre source, et sur le dépôt de chaque projet.

| Bibliothèque | Rôle | Licence |
|---|---|---|
| PyTorch (`torch`) | inférence du modèle GLiNER | BSD-3-Clause |
| Transformers, `tokenizers`, `huggingface_hub`, `safetensors` | chargement/téléchargement du modèle | Apache-2.0 |
| GLiNER (`gliner`) | détection d'entités | Apache-2.0 |
| NumPy | calcul numérique | BSD-3-Clause |
| `openpyxl` | lecture/écriture XLSX | MIT |
| PyYAML | configuration | MIT |
| `regex` | expressions régulières | Apache-2.0 |
| `certifi` | certificats racine | MPL-2.0 |

> Le modèle GLiNER lui-même (`urchade/gliner_multi-v2.1`, poids Apache-2.0) est
> **téléchargé au premier lancement** et n'est pas redistribué dans l'exécutable.

Cette liste couvre les composants notables ; la distribution peut embarquer des
dépendances transitives supplémentaires, chacune conservant sa propre licence.
