from dataclasses import dataclass


@dataclass
class TextUnit:
    """Un paragraphe : une liste de « runs » (objets exposant un attribut
    `.text` mutable — Run python-docx/pptx ou XmlRun) et une localisation
    d'audit lisible (« Corps », « Tableau L2C3 », « Slide 3 / Notes »)."""
    runs: list
    location: str

    def text(self) -> str:
        return "".join((r.text or "") for r in self.runs)
