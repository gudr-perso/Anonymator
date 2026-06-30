# -*- coding: utf-8 -*-
from anonymator.model import Entity
from anonymator.referential import Referential
from anonymator.anonymize import apply_masking

def test_replaces_spans_with_tags():
    ref = Referential.load_default()
    text = "Claire Martin a écrit à c@x.fr"
    ents = [Entity("PERSON", "Claire Martin", 0, 13, "ner", 1.0),
            Entity("EMAIL", "c@x.fr", 24, 30, "deterministic", 1.0)]
    assert apply_masking(text, ents, ref) == "[PERSONNE] a écrit à [EMAIL]"

def test_single_entity_replacement():
    ref = Referential.load_default()
    text = "c@x.fr"
    ents = [Entity("EMAIL", "c@x.fr", 0, 6, "deterministic", 1.0)]
    assert apply_masking(text, ents, ref) == "[EMAIL]"

def test_overlapping_entities_are_merged_before_masking():
    ref = Referential.load_default()
    text = "Claire Martin"
    ents = [Entity("PERSON", "Claire Martin", 0, 13, "ner", 1.0),
            Entity("PERSON", "Martin", 7, 13, "ner", 0.5)]
    # entrée non fusionnée avec chevauchement : le span le plus fort/long gagne,
    # un seul remplacement, pas de corruption
    assert apply_masking(text, ents, ref) == "[PERSONNE]"

def test_only_masks_provided_entities():
    ref = Referential.load_default()
    text = "Zoé reste"
    assert apply_masking(text, [], ref) == "Zoé reste"
