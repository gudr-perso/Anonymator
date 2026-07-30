from anonymator.model import Entity
from anonymator.deterministic import detect_deterministic
from anonymator.secrets_detect import detect_secrets
from anonymator.merge import merge_entities
from anonymator.ner import NerDetector
from anonymator.referential import Referential
from anonymator.user_rules import detect_forced, apply_allow


def detect_column(value: str, etype: str, ref: Referential,
                  force: bool = False) -> list[Entity]:
    """Détection d'une cellule appartenant à une colonne typée.

    Le type vient de la colonne (en-tête ou contenu homogène), pas du contenu
    de la cellule : la cellule entière est l'entité. C'est ce qui garantit un
    traitement identique sur toute la colonne, là où le NER, appelé sur une
    valeur isolée et sans contexte, reconnaît « Nantes » mais pas
    « La Rochelle ». Les règles utilisateur « conserver » restent prioritaires.

    `force=True` court-circuite le garde `is_active` : c'est le chemin d'un
    forçage manuel de colonne, décision explicite de l'utilisateur devant son
    fichier, qui doit primer sur le défaut du référentiel (ex. masquer une
    colonne de codes postaux, type inactif par défaut). La détection
    automatique, elle, appelle sans `force` et respecte l'état du référentiel.
    """
    if not force and not ref.is_active(etype):
        return []
    stripped = value.strip()
    if not stripped:
        return []
    start = len(value) - len(value.lstrip())
    entity = Entity(etype, stripped, start, start + len(stripped), "column", 1.0)
    return apply_allow([entity], ref.user_rules)


def detect(text: str, ner: NerDetector, ref: Referential) -> list[Entity]:
    rules = ref.user_rules
    deterministic = [e for e in detect_deterministic(text) if ref.is_active(e.type)]
    secrets = [e for e in detect_secrets(text) if ref.is_active(e.type)]
    labels = ref.active_ner_labels()
    ner_entities = ner.detect(text, labels) if labels else []
    ner_entities = [e for e in ner_entities if ref.is_active(e.type)]
    forced = detect_forced(text, rules)
    merged = merge_entities(deterministic + secrets + ner_entities + forced)
    return apply_allow(merged, rules)
