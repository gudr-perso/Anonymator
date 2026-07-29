import os
from pathlib import Path

MODEL_NAME = "urchade/gliner_multi-v2.1"
_CACHE_SUBDIR = "models--urchade--gliner_multi-v2.1"

# Poids du dépôt, relevé via l'API HuggingFace (siblings, 2026-07-29) :
#   pytorch_model.bin   1 155 900 362
#   model.safetensors   1 155 830 112   (mêmes poids, second format)
#   gliner_config.json / README / .gitattributes      6 766
# `snapshot_download` récupère tout, d'où un total juste au-dessus de la limite
# d'un entier 32 bits — c'est ce qui faisait déborder la barre de progression.
MODEL_DOWNLOAD_SIZE_BYTES = 2_311_737_240
# Libellé unique affiché dans l'IHM : deux textes figés à « ~300 Mo » avaient
# divergé de la réalité, on les dérive maintenant de la valeur ci-dessus.
MODEL_DOWNLOAD_SIZE = f"~{MODEL_DOWNLOAD_SIZE_BYTES / 1024 ** 3:.1f} Go".replace(".", ",")

def model_cache_dir() -> Path:
    if hub_cache := os.environ.get("HUGGINGFACE_HUB_CACHE"):
        return Path(hub_cache) / _CACHE_SUBDIR
    if hf_home := os.environ.get("HF_HOME"):
        return Path(hf_home) / "hub" / _CACHE_SUBDIR
    return Path.home() / ".cache" / "huggingface" / "hub" / _CACHE_SUBDIR

# Fichiers de poids chargés par `GLiNER.from_pretrained` : leur présence est le
# seul signe fiable d'un instantané exploitable.
_WEIGHT_FILES = ("pytorch_model.bin", "model.safetensors")


def is_model_available() -> bool:
    """Vrai seulement si un instantané *utilisable* est en cache.

    Il ne suffit pas que `snapshots/` existe : un téléchargement interrompu
    crée le dossier de révision **vide** (les octets restent dans des blobs
    `.incomplete`). L'app se croyait alors en mode complet et affichait
    « ✅ Installé (0 Mo) » alors que le chargement échouait."""
    snapshots = model_cache_dir() / "snapshots"
    if not snapshots.exists():
        return False
    return any(
        (rev / name).exists()
        for rev in snapshots.iterdir() if rev.is_dir()
        for name in _WEIGHT_FILES
    )

def installed_size() -> int | None:
    """Taille en octets du modèle en cache, ou None s'il n'est pas installé."""
    if not is_model_available():
        return None
    d = model_cache_dir()
    blobs = d / "blobs"
    if blobs.exists():
        blob_size = sum(p.stat().st_size for p in blobs.rglob("*") if p.is_file())
        if blob_size:
            return blob_size
    # Windows sans lien symbolique : les fichiers réels sont copiés dans
    # snapshots/ et blobs/ reste vide. On somme snapshots/ sans suivre les
    # symlinks (pour éviter le double comptage sur les systèmes qui en ont).
    snapshots = d / "snapshots"
    return sum(
        p.stat().st_size
        for p in snapshots.rglob("*")
        if p.is_file() and not p.is_symlink()
    )
