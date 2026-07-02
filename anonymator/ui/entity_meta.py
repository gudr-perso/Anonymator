"""Métadonnées d'affichage des types d'entités (libellé, sous-titre, icône).
Présentation uniquement — la liste des codes fait foi dans settings_screen._TYPES."""
from dataclasses import dataclass


@dataclass(frozen=True)
class EntityMeta:
    label: str
    subtitle: str
    icon: str


ENTITY_META = {
    "PERSON":      EntityMeta("PERSON", "Noms et prénoms de personnes", "person"),
    "ADDRESS":     EntityMeta("ADDRESS", "Adresses postales", "map-pin"),
    "ORG":         EntityMeta("ORG", "Organisations, entreprises", "building"),
    "EMAIL":       EntityMeta("EMAIL", "Adresses e-mail", "mail"),
    "PHONE":       EntityMeta("PHONE", "Numéros de téléphone", "phone"),
    "IBAN":        EntityMeta("IBAN", "Coordonnées bancaires", "credit-card"),
    "BIC":         EntityMeta("BIC", "Codes banque · SWIFT", "scale"),
    "SIREN":       EntityMeta("SIREN", "Identifiants d'entreprise", "building"),
    "SIRET":       EntityMeta("SIRET", "Établissements (SIREN + NIC)", "building"),
    "NIR":         EntityMeta("NIR", "Numéro de sécurité sociale", "id-card"),
    "POSTAL_CODE": EntityMeta("POSTAL_CODE", "Codes postaux", "map-pin"),
    "URL":         EntityMeta("URL", "Adresses web", "globe"),
    "LOGIN":       EntityMeta("LOGIN", "Identifiants de connexion", "user"),
    "PASSWORD":    EntityMeta("PASSWORD", "Mots de passe", "lock"),
}
