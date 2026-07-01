# tests/pdf_fixtures.py
from pathlib import Path
import fitz


def make_native_pdf(path: Path, text: str = "Contact Claire Martin claire@example.com",
                    title: str = "", author: str = "") -> Path:
    """PDF natif : une page avec du texte sélectionnable à (72, 72)."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    if title or author:
        doc.set_metadata({"title": title, "author": author})
    doc.save(str(path))
    doc.close()
    return path


def make_repeat_pdf(path: Path) -> Path:
    """Une même phrase présente deux fois, sur deux lignes distinctes."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "GUILLAUME DROGLAND habite ici", fontsize=11)
    page.insert_text((72, 200), "Titulaire GUILLAUME DROGLAND", fontsize=11)
    doc.save(str(path))
    doc.close()
    return path


def make_scanned_pdf(path: Path) -> Path:
    """PDF « scanné » : une page avec seulement une image, aucune couche texte."""
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 200))
    pix.clear_with(220)
    page.insert_image(fitz.Rect(50, 50, 250, 250), pixmap=pix)
    doc.save(str(path))
    doc.close()
    return path


def make_layout_pdf(path: Path) -> Path:
    """Deux colonnes horizontales + un bloc de marge pivoté (vertical)."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 120), "Titulaire GUILLAUME DROGLAND", fontsize=11)
    page.insert_text((330, 120), "Montant total", fontsize=11)
    page.insert_text((40, 400), "Vagram Paris Cedex", fontsize=9, rotate=90)
    doc.save(str(path))
    doc.close()
    return path


def make_encrypted_pdf(path: Path, password: str = "secret") -> Path:
    """PDF chiffré (mot de passe utilisateur)."""
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "secret content", fontsize=12)
    doc.save(str(path), encryption=fitz.PDF_ENCRYPT_AES_256,
             owner_pw=password, user_pw=password)
    doc.close()
    return path
