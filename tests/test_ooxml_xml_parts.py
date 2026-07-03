from lxml import etree
from anonymator.files.ooxml.xml_parts import XmlRun

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _run(text):
    r = etree.SubElement(etree.Element(f"{{{W}}}p"), f"{{{W}}}r")
    t = etree.SubElement(r, f"{{{W}}}t")
    t.text = text
    return r


def test_xmlrun_reads_text():
    assert XmlRun(_run("Bonjour")).text == "Bonjour"


def test_xmlrun_writes_text_into_first_t():
    r = _run("Bonjour")
    run = XmlRun(r)
    run.text = "Salut"
    assert run.text == "Salut"
    assert r.find(f"{{{W}}}t").text == "Salut"


def test_xmlrun_sets_space_preserve_on_leading_space():
    r = _run("x")
    XmlRun(r).text = " abc "
    t = r.find(f"{{{W}}}t")
    assert t.get("{http://www.w3.org/XML/1998/namespace}space") == "preserve"


import zipfile
from anonymator.report.audit import AuditReport
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.ooxml import xml_parts


def _para(text):
    return f'<w:p xmlns:w="{W}"><w:r><w:t>{text}</w:t></w:r></w:p>'


def _make_docx_zip(path):
    parts = {
        "[Content_Types].xml": '<?xml version="1.0"?><Types/>',
        "word/document.xml":
            f'<?xml version="1.0"?><w:document xmlns:w="{W}"><w:body/></w:document>',
        "word/comments.xml":
            f'<?xml version="1.0"?><w:comments xmlns:w="{W}">'
            f'<w:comment w:id="1">{_para("Vu par Claire Martin")}</w:comment>'
            f'</w:comments>',
        "word/footnotes.xml":
            f'<?xml version="1.0"?><w:footnotes xmlns:w="{W}">'
            f'<w:footnote w:type="separator" w:id="1">{_para("")}</w:footnote>'
            f'<w:footnote w:id="2">{_para("Note de Claire Martin")}</w:footnote>'
            f'</w:footnotes>',
        "docProps/core.xml":
            '<?xml version="1.0"?><cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">'
            '<dc:creator>Alice Durand</dc:creator></cp:coreProperties>',
    }
    with zipfile.ZipFile(path, "w") as z:
        for name, blob in parts.items():
            z.writestr(name, blob)


def test_postprocess_docx_masks_parts_and_purges_metadata(tmp_path):
    path = tmp_path / "d.docx"
    _make_docx_zip(path)
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    report = xml_parts.postprocess_docx(path, ner, ref, AuditReport())
    with zipfile.ZipFile(path) as z:
        comments = z.read("word/comments.xml").decode("utf-8")
        footnotes = z.read("word/footnotes.xml").decode("utf-8")
        core = z.read("docProps/core.xml").decode("utf-8")
    assert "Claire Martin" not in comments and "[PERSONNE]" in comments
    assert "Claire Martin" not in footnotes and "[PERSONNE]" in footnotes
    assert "Alice Durand" not in core
    assert any(r["original"] == "Claire Martin" for r in report.to_rows())
