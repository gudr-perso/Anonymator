ENTITY_COLORS = {
    "PERSON":      "#2d6cdf",
    "ADDRESS":     "#1f9d57",
    "ORG":         "#0c8a93",
    "EMAIL":       "#8a3ffc",
    "PHONE":       "#d97400",
    "IBAN":        "#d62828",
    "BIC":         "#b5179e",
    "SIREN":       "#3a0ca3",
    "SIRET":       "#7209b7",
    "NIR":         "#c1121f",
    "POSTAL_CODE": "#4d908e",
    "URL":         "#577590",
}
_FALLBACK = "#8499AB"


def color_for(code: str) -> str:
    return ENTITY_COLORS.get(code, _FALLBACK)
