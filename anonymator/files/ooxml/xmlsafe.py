"""Analyse XML durcie, partagée par tout ce qui lit une partie OOXML.

Le XML traité vient d'un fichier reçu d'un tiers. Le parseur par défaut de lxml
ne résout plus les entités externes depuis la 6.1, mais c'est un défaut récent
et le projet ne l'épingle pas : `lxml` n'arrive que transitivement, python-docx
et python-pptx ne réclamant que `lxml>=3.1.0`. Une installation qui résout une
version antérieure rendrait la lecture d'un fichier local possible depuis un
document piégé, puis son exfiltration dans le document « anonymisé » que
l'utilisateur renvoie à son correspondant.

On ne dépend donc pas du défaut. Même posture qu'openpyxl
(`XMLParser(resolve_entities=False)`) et python-docx (`oxml_parser`).
"""
from lxml import etree

SAFE_PARSER = etree.XMLParser(resolve_entities=False, load_dtd=False,
                              no_network=True, huge_tree=False)


def parse(xml_bytes: bytes):
    """Arbre d'une partie XML, entités externes non résolues."""
    return etree.fromstring(xml_bytes, SAFE_PARSER)


def serialize(root) -> bytes:
    """Sérialisation d'une partie OOXML : déclaration XML, UTF-8, standalone."""
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                          standalone=True)
