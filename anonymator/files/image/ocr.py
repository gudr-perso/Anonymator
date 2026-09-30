# anonymator/files/image/ocr.py
"""Moteur OCR derrière un protocole, sur le modèle de anonymator/ner.py.

Le protocole permet trois choses : tester toute la chaîne hors ligne avec
FakeOcr, offrir un mode dégradé avec NullOcr (tracé manuel seul), et changer de
moteur sans toucher au reste du code."""
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

Rect = tuple[float, float, float, float]


@dataclass(frozen=True)
class OcrBox:
    text: str
    rect: Rect          # rectangle englobant, en pixels de l'image source
    confidence: float

    @classmethod
    def from_quad(cls, text: str, quad, confidence: float) -> "OcrBox":
        """Réduit un quadrilatère (4 coins) à son rectangle englobant.

        Un englobant déborde toujours un peu : en caviardage, déborder est sûr,
        rogner ne l'est pas."""
        xs = [float(p[0]) for p in quad]
        ys = [float(p[1]) for p in quad]
        return cls(text, (min(xs), min(ys), max(xs), max(ys)), float(confidence))


class OcrEngine(Protocol):
    def read(self, image) -> list[OcrBox]: ...


class FakeOcr:
    """Moteur déterministe pour les tests : rend les boîtes qu'on lui donne."""
    def __init__(self, boxes: list[OcrBox]):
        self._boxes = list(boxes)

    def read(self, image) -> list[OcrBox]:
        return list(self._boxes)


class NullOcr:
    """Moteur vide : aucune lecture. Sert le mode dégradé (dépendance OCR
    absente) — le tracé manuel de zones reste disponible."""
    def read(self, image) -> list[OcrBox]:
        return []


# --- moteur réel ---

def _load_rapidocr():
    """Import paresseux : charger RapidOCR tire onnxruntime et 32 Mo de modèles.
    Isolé dans une fonction pour être remplaçable en test."""
    from rapidocr import RapidOCR
    return RapidOCR


_MODEL_FILES = {
    "Det.model_path": "PP-OCRv6_det_small.onnx",
    "Rec.model_path": "PP-OCRv6_rec_small.onnx",
    "Cls.model_path": "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
}


def _models_dir() -> Path:
    """Dossier des modèles livrés avec RapidOCR.

    Dans un exe PyInstaller, `rapidocr.__file__` est un chemin **virtuel** sous
    `sys._MEIPASS` : le module vit dans l'archive, pas sur disque. Son dossier
    parent, lui, existe bien — c'est là que le `.spec` dépose les données. Le
    repli explicite sur `_MEIPASS` couvre le cas où cette équivalence ne
    tiendrait pas."""
    import rapidocr

    models = Path(rapidocr.__file__).parent / "models"
    if models.is_dir():
        return models
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) / "rapidocr" / "models" if base else models


def _bundled_model_paths() -> dict[str, str]:
    """Chemins des trois modèles livrés dans la wheel.

    On les impose explicitement : laissés à null, les paramètres Det/Rec/Cls
    font résoudre le modèle par default_models.yaml, qui pointe vers un
    hébergeur externe. L'application promet « aucun appel réseau en usage
    normal » — ce verrou est ce qui tient la promesse.

    Une absence est signalée ici, fort et clair : l'appelant la remonte à
    l'utilisateur. Un empaquetage sans les modèles ne doit pas se traduire par
    une analyse qui ne rend rien."""
    models = _models_dir()
    manquants = [nom for nom in _MODEL_FILES.values()
                 if not (models / nom).exists()]
    if manquants:
        raise FileNotFoundError(
            "Modèles de reconnaissance de texte introuvables dans "
            f"{models} : {', '.join(manquants)}. "
            "L'application a probablement été empaquetée sans eux.")
    return {cle: str(models / nom) for cle, nom in _MODEL_FILES.items()}


# Côté le plus long au-delà duquel on réduit l'image avant l'OCR. RapidOCR
# redimensionne déjà en interne (Global.max_side_len), mais sans contrat
# documenté sur le remappage des boîtes : on maîtrise donc l'échelle nous-mêmes,
# et on remet les coordonnées à l'échelle de l'image d'origine. Une erreur ici
# ne se verrait pas à la détection — elle ferait caviarder à côté.
MAX_SIDE = 2000


def _split_into_words(lignes, word_results) -> list[OcrBox]:
    """Une OcrBox par mot, en repliant sur la ligne quand le découpage manque.

    `word_results` est une suite parallèle aux lignes : pour chacune, un tuple
    de triplets `(texte, score, quadrilatère)`. Un quadrilatère peut être absent
    — le moteur n'a pas su découper cette ligne. On garde alors sa boîte
    entière : caviarder trop large reste sûr, perdre la zone ne l'est pas."""
    if not word_results:
        return [OcrBox.from_quad(t, q, s) for q, t, s in lignes]

    boxes: list[OcrBox] = []
    for index, (quad, texte, score) in enumerate(lignes):
        mots = word_results[index] if index < len(word_results) else None
        decoupables = [m for m in (mots or ())
                       if len(m) > 2 and m[2] and m[0]]
        if mots and len(decoupables) == len([m for m in mots if m[0]]):
            boxes.extend(OcrBox.from_quad(m[0], m[2], m[1]) for m in decoupables)
        else:
            boxes.append(OcrBox.from_quad(texte, quad, score))
    return boxes


class RapidOcrEngine:
    """Adaptateur autour de RapidOCR (ONNX). Importé paresseusement."""

    def __init__(self, text_score: float = 0.5):
        params = _bundled_model_paths()
        params["Global.text_score"] = text_score
        self._engine = _load_rapidocr()(params=params)

    def read(self, image) -> list[OcrBox]:
        import numpy as np

        img = image.convert("RGB")
        scale = 1.0
        longest = max(img.size)
        if longest > MAX_SIDE:
            scale = longest / MAX_SIDE
            img = img.resize((max(1, round(img.width / scale)),
                              max(1, round(img.height / scale))))
        # return_word_box : sans lui, le moteur rend UNE boîte par ligne. Prise
        # pour un mot, elle fait caviarder la phrase entière — masquer un nom
        # effaçait « Pour toute question, notre comptable … reste ». La
        # granularité du rectangle, c'est la granularité du caviardage.
        result = self._engine(np.array(img), return_word_box=True)
        quads = result.boxes if result.boxes is not None else []
        txts = result.txts or ()
        scores = result.scores or ()
        lignes = list(zip(quads, txts, scores))
        boxes = _split_into_words(lignes, getattr(result, "word_results", None))
        if scale == 1.0:
            return boxes
        return [OcrBox(b.text,
                       tuple(v * scale for v in b.rect),
                       b.confidence)
                for b in boxes]
