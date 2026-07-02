DEFAULT_THEME = "cuma"

THEMES = {
    "cuma": {"primary": "#31B700", "action": "#00965E", "dark": "#063b27",
             "accent": "#E8621A", "accent_hover": "#C9500F", "bg": "#FFFFFF",
             "text": "#10331F",
             "bg_hero": "#E8F3EA", "surface": "#FFFFFF", "surface_alt": "#F3FAF4",
             "border": "#E2E8E4", "text_muted": "#6B7C72",
             "info": "#4FA8D8", "info_hover": "#3D93C2",
             "grid_bg": "#E8F3EA", "grid_line": "#E1EBE3",
             "hero_text": "#10331F", "hero_muted": "#6B7C72",
             "toggle_off": "#C7D2CC", "logo": "logo.png"},
    "cap":  {"primary": "#2aa6e8", "action": "#138fdb", "dark": "#050c3f",
             "accent": "#f36100", "accent_hover": "#d15400", "bg": "#FFFFFF",
             "text": "#050c3f",
             "bg_hero": "#0a1556", "surface": "#FFFFFF", "surface_alt": "#EEF5FB",
             "border": "#DCE6F0", "text_muted": "#64748B",
             "info": "#2aa6e8", "info_hover": "#138fdb",
             "grid_bg": "#0a1556", "grid_line": "#1e2a63",
             "hero_text": "#FFFFFF", "hero_muted": "rgba(255,255,255,0.82)",
             "toggle_off": "#C3CCE0", "logo": "logo-cap.png"},
}

_active_theme = DEFAULT_THEME


def set_active_theme(name: str) -> None:
    """Positionne le thème lu par la couche peinte / icônes."""
    global _active_theme
    _active_theme = name if name in THEMES else DEFAULT_THEME


def active_theme() -> str:
    return _active_theme


def tokens(theme: str | None = None) -> dict:
    return THEMES.get(theme or _active_theme, THEMES[DEFAULT_THEME])


def color(role: str, theme: str | None = None) -> str:
    """Couleur d'un rôle dans le thème actif (ou `theme` si précisé)."""
    return tokens(theme)[role]


THEME_LABELS = {
    "cuma": "CUMA — vert identitaire",
    "cap":  "CAP — bleu",
}


def label_for_theme(theme: str) -> str:
    return THEME_LABELS.get(theme, theme)


def theme_for_label(label: str) -> str:
    for key, lbl in THEME_LABELS.items():
        if lbl == label:
            return key
    return DEFAULT_THEME

_TEMPLATE = """
QWidget {{ background: {bg}; color: {text};
          font-family: 'Inter','Segoe UI',sans-serif; font-size: 14px; }}
QLabel {{ background: transparent; }}
QLabel#title {{ font-family: 'Space Grotesk','Segoe UI',sans-serif;
               font-size: 31px; font-weight: 700; color: {text}; }}
QLabel#muted {{ color: {text_muted}; }}
QLabel#sectionLabel {{ color: {text_muted}; font-size: 11px; font-weight: 700;
                      letter-spacing: 1px; }}
#HeaderBand {{ background: {surface}; border-bottom: 1px solid {border}; }}
#Card {{ background: {surface}; border: 1px solid {border}; border-radius: 10px; }}
#StatCard {{ background: {surface_alt}; border: 1px solid {border}; border-radius: 10px; }}
#NavCard {{ background: {surface}; border: 1px solid {border}; border-radius: 10px; }}
#NavCard:hover {{ background: {surface_alt}; border-color: {action}; }}
QPushButton#primary {{ background: {action}; color: white; border: none;
                      border-radius: 8px; padding: 10px 18px; font-weight: 600; }}
QPushButton#primary:hover {{ background: {primary}; }}
QPushButton#info {{ background: {info}; color: white; border: none;
                   border-radius: 8px; padding: 10px 18px; font-weight: 600; }}
QPushButton#info:hover {{ background: {info_hover}; }}
QPushButton#secondary {{ background: transparent; color: {text};
                        border: 1px solid {border}; border-radius: 8px; padding: 10px 18px; }}
QPushButton#ghost {{ background: transparent; color: {action}; border: none; padding: 8px 14px; }}
/* Boutons de la barre d'action (écrans Fichier & PDF) — aplats pleins charte */
QPushButton#navHome {{ background: {accent}; color: white; border: none;
                      border-radius: 8px; padding: 10px 18px; font-weight: 600; }}
QPushButton#navHome:hover {{ background: {accent_hover}; }}
QPushButton#navOpen {{ background: {dark}; color: white; border: none;
                      border-radius: 8px; padding: 10px 18px; font-weight: 600; }}
QPushButton#navOpen:hover {{ background: {action}; }}
QPushButton#navTool {{ background: {primary}; color: white; border: none;
                      border-radius: 8px; padding: 10px 18px; font-weight: 600; }}
QPushButton#navTool:hover {{ background: {action}; }}
QPushButton#navTool:checked {{ background: {dark}; }}
/* Bandeau blanc (barre fichier + boutons) posé sur la grille */
#ActionBand {{ background: {surface}; border-bottom: 1px solid {border}; }}
#PagerBar {{ background: transparent; }}
#Crumb {{ background: {surface_alt}; border: 1px solid {border}; border-radius: 18px; }}
QPushButton#crumb {{ background: transparent; color: {text_muted}; border: none;
                    padding: 6px 14px; border-radius: 14px; }}
QPushButton#crumb:hover {{ color: {text}; }}
QPushButton#crumbActive {{ background: {surface}; color: {action}; border: 1px solid {border};
                          border-radius: 14px; padding: 6px 14px; font-weight: 700; }}
QLabel#busyOverlay {{ background: rgba(255,255,255,0.82); color: {action};
                     font-size: 17px; font-weight: 700; }}
QLabel#fileName {{ font-size: 15px; font-weight: 700; color: {text}; }}
QLabel#fileMeta {{ color: {text_muted}; font-size: 12px; }}
QLabel#occBadge {{ background: {surface_alt}; color: {action}; border: 1px solid {border};
                  border-radius: 9px; padding: 2px 10px; font-size: 11px; font-weight: 700; }}
QLabel#hint {{ color: {text_muted}; font-size: 12px; }}
QTableWidget {{ background: {surface}; border: none; gridline-color: {border};
               selection-background-color: {surface_alt}; selection-color: {text}; }}
QTableWidget::item {{ padding: 5px 8px; }}
QHeaderView::section {{ background: {surface_alt}; color: {text_muted};
                       padding: 7px 10px; border: none; border-bottom: 1px solid {border};
                       font-size: 11px; font-weight: 700; letter-spacing: 0.5px; }}
QTableCornerButton::section {{ background: {surface_alt}; border: none;
                              border-bottom: 1px solid {border}; }}
QTreeWidget {{ background: {surface}; border: none; outline: 0; }}
QTreeWidget::item {{ padding: 5px 2px; }}
QTreeWidget::item:selected {{ background: {surface_alt}; color: {text}; }}
QPushButton#pager {{ background: {surface}; color: {text}; border: 1px solid {border};
                    border-radius: 8px; padding: 7px 14px; }}
QPushButton#pager:hover {{ background: {surface_alt}; border-color: {action}; }}
QPushButton#pager:disabled {{ color: {text_muted}; border-color: {border}; }}
QLabel#pageInfo {{ color: {text}; font-weight: 600; }}
#NavBand {{ background: {surface}; border-bottom: 1px solid {border}; }}
QPushButton#tab {{ background: transparent; color: {text_muted}; border: none;
                  border-bottom: 3px solid transparent; padding: 12px 14px; font-weight: 600; }}
QPushButton#tab:hover {{ color: {text}; }}
QPushButton#tabActive {{ background: transparent; color: {action}; border: none;
                        border-bottom: 3px solid {action}; padding: 12px 14px; font-weight: 700; }}
QPushButton#tabActive:disabled {{ color: {action}; }}
#EntityCard {{ background: {surface}; border: 1px solid {border}; border-radius: 10px; }}
#EntityCard:hover {{ border-color: {action}; }}
"""


def build_qss(theme: str) -> str:
    tokens = THEMES.get(theme, THEMES[DEFAULT_THEME])
    return _TEMPLATE.format(**tokens)
