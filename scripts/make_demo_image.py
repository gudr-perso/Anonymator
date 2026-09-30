"""Génère l'image de démonstration du mode Image : exemples/capture_mail_demo.png

    .venv/Scripts/python scripts/make_demo_image.py

Simule la capture d'écran d'un client de messagerie — le cas d'usage le plus
courant : on veut montrer un échange sans diffuser les coordonnées qu'il porte.

**Toutes les données sont fictives.** Elles reprennent l'univers de
`clients_demo.csv` (Ateliers Tanguy EURL, Delphine Salvatore, Nantes), pour
qu'on puisse recouper les deux fichiers de démonstration.

L'image est conçue pour faire travailler les deux moitiés du mode Image :

- ce que les **règles** trouvent seules, sans le modèle GLiNER : e-mail,
  téléphone, IBAN (clé mod 97 valide), SIRET (clé de Luhn valide) ;
- ce que le **modèle** ajoute s'il est installé : noms de personnes,
  organisation, adresse postale ;
- ce qu'**aucun des deux** ne peut voir, et qui oblige à tracer une zone à la
  main : une signature manuscrite et une pastille d'avatar aux initiales.

Cette dernière catégorie est le cœur de la démonstration : elle montre pourquoi
l'application *propose* et pourquoi l'utilisateur doit *relire*.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SORTIE = Path(__file__).resolve().parent.parent / "exemples" / "capture_mail_demo.png"

LARGEUR, HAUTEUR = 1120, 760

# Palette neutre : l'image ne doit évoquer aucune messagerie réelle ni aucune
# des éditions diffusées.
FOND = (247, 248, 250)
BARRE = (54, 60, 74)
BLANC = (255, 255, 255)
TEXTE = (28, 32, 40)
GRIS = (120, 128, 140)
TRAIT = (222, 226, 232)
ACCENT = (58, 96, 160)

# Polices : on cherche une TrueType, faute de quoi la police bitmap de Pillow
# ne rendrait pas les accents.
_POLICES = [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
_POLICES_GRAS = [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _police(chemins: list[str], taille: int) -> ImageFont.FreeTypeFont:
    for chemin in chemins:
        if Path(chemin).exists():
            return ImageFont.truetype(chemin, taille)
    raise SystemExit(
        "Aucune police TrueType trouvée. Renseignez-en une dans _POLICES : "
        "la police par défaut de Pillow ne rend pas les accents."
    )


def _signature(d: ImageDraw.ImageDraw, x: int, y: int) -> None:
    """Griffe manuscrite : illisible par la reconnaissance de caractères.

    C'est le piège pédagogique de l'image — l'utilisateur doit la masquer
    lui-même avec « Zone manuelle »."""
    trace = [
        (0, 30), (14, 8), (24, 34), (36, 4), (48, 32), (62, 12), (74, 30),
        (92, 6), (104, 28), (118, 14), (134, 30), (150, 10), (168, 26),
        (186, 16), (202, 28),
    ]
    points = [(x + dx, y + dy) for dx, dy in trace]
    d.line(points, fill=(38, 54, 110), width=3, joint="curve")
    d.arc([x + 150, y + 6, x + 215, y + 42], start=200, end=20,
          fill=(38, 54, 110), width=3)


def construire() -> Image.Image:
    img = Image.new("RGB", (LARGEUR, HAUTEUR), FOND)
    d = ImageDraw.Draw(img)

    f_titre = _police(_POLICES_GRAS, 19)
    f_objet = _police(_POLICES_GRAS, 24)
    f_gras = _police(_POLICES_GRAS, 17)
    f_normal = _police(_POLICES, 17)
    f_petit = _police(_POLICES, 15)

    # --- barre de fenêtre ---
    d.rectangle([0, 0, LARGEUR, 52], fill=BARRE)
    d.text((24, 15), "Messagerie — Boîte de réception", fill=BLANC, font=f_titre)
    for i, couleur in enumerate([(240, 96, 88), (240, 190, 80), (110, 200, 120)]):
        d.ellipse([LARGEUR - 96 + i * 26, 20, LARGEUR - 82 + i * 26, 34],
                  fill=couleur)

    # --- carte du message ---
    d.rounded_rectangle([28, 78, LARGEUR - 28, HAUTEUR - 28], radius=10,
                        fill=BLANC, outline=TRAIT, width=1)

    # Pastille d'avatar : initiales dans un rond. Aucun texte exploitable pour
    # la reconnaissance de caractères → à masquer à la main.
    d.ellipse([56, 110, 116, 170], fill=(206, 219, 240))
    d.text((72, 128), "DS", fill=ACCENT, font=f_objet)

    d.text((136, 112), "Delphine Salvatore", fill=TEXTE, font=f_gras)
    d.text((136, 138), "delphine.salvatore@ateliers-tanguy.net", fill=ACCENT,
           font=f_petit)
    d.text((136, 160), "mardi 14 janvier 2025 à 09:12", fill=GRIS, font=f_petit)
    d.text((LARGEUR - 300, 112), "À : compta@exemple-cabinet.fr", fill=GRIS,
           font=f_petit)

    d.line([56, 196, LARGEUR - 56, 196], fill=TRAIT, width=1)
    d.text((56, 214), "Objet : Coordonnées bancaires pour le prélèvement",
           fill=TEXTE, font=f_objet)

    corps = [
        ("normal", "Bonjour,"),
        ("vide", ""),
        ("normal", "Comme convenu au téléphone, voici les éléments pour la mise"),
        ("normal", "en place du prélèvement automatique de nos cotisations."),
        ("vide", ""),
        ("gras", "Ateliers Tanguy EURL"),
        ("normal", "14 rue des Charmilles, 44000 Nantes"),
        ("normal", "SIRET : 404 833 048 00022"),
        ("normal", "IBAN : FR76 3000 6000 0112 3456 7890 189"),
        ("vide", ""),
        ("normal", "Pour toute question, notre comptable Damien Lacroix reste"),
        ("normal", "joignable au 05 32 14 79 60."),
        ("vide", ""),
        ("normal", "Bien cordialement,"),
    ]
    y = 262
    for style, ligne in corps:
        if style == "vide":
            y += 12
            continue
        d.text((56, y), ligne, fill=TEXTE,
               font=f_gras if style == "gras" else f_normal)
        y += 27

    # --- signature manuscrite ---
    _signature(d, 60, y + 6)
    d.text((56, y + 62), "Delphine Salvatore", fill=TEXTE, font=f_gras)
    d.text((56, y + 84), "Gérante — Ateliers Tanguy EURL", fill=GRIS, font=f_petit)

    return img


def main() -> None:
    img = construire()
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    img.save(SORTIE)
    print(f"écrit : {SORTIE}  ({img.width}x{img.height})")


if __name__ == "__main__":
    main()
