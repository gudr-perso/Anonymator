from anonymator.files.ooxml import metadata

CORE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<cp:coreProperties '
    'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/">'
    '<dc:creator>Alice Durand</dc:creator>'
    '<cp:lastModifiedBy>Bob Martin</cp:lastModifiedBy>'
    '<dc:title>Rapport confidentiel</dc:title>'
    '</cp:coreProperties>'
).encode("utf-8")

APP = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Properties '
    'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
    '<Company>ACME SARL</Company><Manager>Alice Durand</Manager>'
    '</Properties>'
).encode("utf-8")


def test_purge_core_xml_blanks_identity_fields():
    out, purged = metadata.purge_core_xml(CORE)
    labels = {label for label, _ in purged}
    assert labels == {"Auteur", "Dernier modifié par", "Titre"}
    assert b"Alice Durand" not in out
    assert b"Bob Martin" not in out
    assert b"Rapport confidentiel" not in out


def test_purge_app_xml_blanks_company_manager():
    out, purged = metadata.purge_app_xml(APP)
    labels = {label for label, _ in purged}
    assert labels == {"Société", "Manager"}
    assert b"ACME" not in out


def test_purge_core_xml_ignores_missing_fields():
    minimal = (
        '<?xml version="1.0"?><cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties">'
        '</cp:coreProperties>'
    ).encode("utf-8")
    out, purged = metadata.purge_core_xml(minimal)
    assert purged == []
