"""Le XML d'un fichier reçu d'un tiers ne doit jamais résoudre une entité externe.

Le parseur par défaut de lxml ne le fait plus depuis la 6.1, mais c'est un
défaut récent et `lxml` n'arrive au projet que transitivement, python-docx et
python-pptx ne réclamant que `lxml>=3.1.0`. Ces tests vérifient le parseur du
projet, pas celui de lxml : ils resteraient verts sur une installation qui
résoudrait une version antérieure.
"""
from pathlib import Path

from lxml import etree

from anonymator.files.ooxml import metadata, xmlsafe


def _doc_with_external_entity(target: Path) -> bytes:
    uri = target.as_uri()
    return (f'<?xml version="1.0"?>'
            f'<!DOCTYPE r [<!ENTITY xxe SYSTEM "{uri}">]>'
            f'<r><a>&xxe;</a></r>').encode()


def test_lecture_de_fichier_local_impossible(tmp_path):
    """Une entité externe ne doit pas ramener le contenu d'un fichier du poste,
    qui repartirait ensuite dans le document « anonymisé »."""
    secret = tmp_path / "secret.txt"
    secret.write_text("TEMOIN-CONTENU-LOCAL", encoding="utf-8")
    xml = _doc_with_external_entity(secret)
    try:
        root = xmlsafe.parse(xml)
    except etree.XMLSyntaxError:
        return          # entité non déclarée : la lecture est refusée d'emblée
    assert "TEMOIN-CONTENU-LOCAL" not in "".join(root.itertext())
    assert b"TEMOIN-CONTENU-LOCAL" not in xmlsafe.serialize(root)


def test_purge_des_metadonnees_utilise_le_parseur_durci(tmp_path):
    """`docProps/core.xml` vient lui aussi du fichier de l'utilisateur."""
    secret = tmp_path / "secret.txt"
    secret.write_text("TEMOIN-CONTENU-LOCAL", encoding="utf-8")
    uri = secret.as_uri()
    xml = (f'<?xml version="1.0"?>'
           f'<!DOCTYPE cp:coreProperties [<!ENTITY xxe SYSTEM "{uri}">]>'
           f'<cp:coreProperties '
           f'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata'
           f'/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:creator>&xxe;</dc:creator></cp:coreProperties>').encode()
    try:
        out, _purged = metadata.purge_core_xml(xml)
    except etree.XMLSyntaxError:
        return
    assert b"TEMOIN-CONTENU-LOCAL" not in out


def test_les_entites_ne_sont_pas_developpees():
    """Garde-fou sur la configuration elle-même, et non sur le défaut de lxml.

    Une entité interne n'est pas une faille, mais ne pas la développer est la
    même position de repli que pour une entité externe : le parseur substitue
    le moins possible."""
    xml = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY i "INTERNE">]><r>&i;</r>'
    root = xmlsafe.parse(xml)
    assert "INTERNE" not in "".join(root.itertext())


def test_le_xml_ordinaire_reste_lisible():
    root = xmlsafe.parse(b'<?xml version="1.0"?><r><a>bonjour</a></r>')
    assert root.find("a").text == "bonjour"
    assert b"bonjour" in xmlsafe.serialize(root)
