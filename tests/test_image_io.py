import pytest
from PIL import Image
from anonymator.files.image import image_io


def test_formats_supportes_contient_les_extensions_attendues():
    assert ".png" in image_io.SUPPORTED_SUFFIXES
    assert ".jpg" in image_io.SUPPORTED_SUFFIXES
    assert ".heic" not in image_io.SUPPORTED_SUFFIXES


def test_format_non_supporte_leve_une_erreur_metier(tmp_path):
    p = tmp_path / "photo.heic"
    p.write_bytes(b"pas une image")
    with pytest.raises(image_io.UnsupportedImageFormat):
        image_io.load_image(p)


def test_fichier_corrompu_leve_une_erreur_metier(tmp_path):
    p = tmp_path / "casse.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n corrompu")
    with pytest.raises(image_io.CorruptImageError):
        image_io.load_image(p)


def test_chargement_rend_une_image_rgb(tmp_path):
    p = tmp_path / "gris.png"
    Image.new("L", (10, 10), 128).save(p)
    assert image_io.load_image(p).mode == "RGB"


def test_orientation_exif_est_appliquee_avant_la_purge(tmp_path):
    # Orientation=6 => rotation de 90° ; une image 20x10 doit ressortir 10x20.
    p = tmp_path / "tournee.jpg"
    img = Image.new("RGB", (20, 10), (10, 20, 30))
    exif = img.getexif()
    exif[274] = 6                      # 274 = tag Orientation
    img.save(p, exif=exif)
    loaded = image_io.load_image(p)
    assert loaded.size == (10, 20)


def test_une_image_animee_est_reduite_a_sa_premiere_vue(tmp_path):
    p = tmp_path / "anime.webp"
    v1 = Image.new("RGB", (10, 10), (255, 0, 0))
    v2 = Image.new("RGB", (10, 10), (0, 0, 255))
    v1.save(p, save_all=True, append_images=[v2], duration=100, loop=0)
    loaded = image_io.load_image(p)
    assert loaded.size == (10, 10)
    # WebP est compressé avec perte : on vérifie la dominante, pas l'égalité
    # exacte. Ce qui compte est que ce soit la vue ROUGE (la première) et non
    # la bleue.
    r, g, b = loaded.getpixel((5, 5))
    assert r > 200 and b < 50


def test_enregistrement_ne_conserve_aucune_metadonnee(tmp_path):
    src = tmp_path / "avec_exif.jpg"
    img = Image.new("RGB", (10, 10), (1, 2, 3))
    exif = img.getexif()
    exif[271] = "MarqueAppareil"       # 271 = Make
    img.save(src, exif=exif)
    out = tmp_path / "sortie.jpg"
    image_io.save_image(image_io.load_image(src), out)
    assert dict(Image.open(out).getexif()) == {}
