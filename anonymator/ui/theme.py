DEFAULT_THEME = "cuma"

THEMES = {
    "cuma": {"primary": "#31B700", "action": "#00965E", "dark": "#063b27",
             "accent": "#E8621A", "bg": "#FFFFFF", "text": "#10331F",
             "bg_hero": "#E8F3EA", "surface": "#FFFFFF", "surface_alt": "#F3FAF4",
             "border": "#E2E8E4", "text_muted": "#6B7C72"},
    "cap":  {"primary": "#1DA8E2", "action": "#1570B8", "dark": "#0D1A35",
             "accent": "#E8621A", "bg": "#FFFFFF", "text": "#1E1E2E",
             "bg_hero": "#EAF4FB", "surface": "#FFFFFF", "surface_alt": "#F4F9FD",
             "border": "#E1E8EF", "text_muted": "#6B7280"},
}

_TEMPLATE = """
QWidget {{ background: {bg}; color: {text};
          font-family: 'Inter','Segoe UI',sans-serif; font-size: 14px; }}
QLabel {{ background: transparent; }}
QLabel#title {{ font-family: 'Space Grotesk','Segoe UI',sans-serif;
               font-size: 26px; font-weight: 700; color: {text}; }}
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
QPushButton#secondary {{ background: transparent; color: {text};
                        border: 1px solid {border}; border-radius: 8px; padding: 10px 18px; }}
QPushButton#ghost {{ background: transparent; color: {action}; border: none; padding: 8px 14px; }}
#Crumb {{ background: {surface_alt}; border: 1px solid {border}; border-radius: 18px; }}
QPushButton#crumb {{ background: transparent; color: {text_muted}; border: none;
                    padding: 6px 14px; border-radius: 14px; }}
QPushButton#crumb:hover {{ color: {text}; }}
QPushButton#crumbActive {{ background: {surface}; color: {action}; border: 1px solid {border};
                          border-radius: 14px; padding: 6px 14px; font-weight: 700; }}
"""


def build_qss(theme: str) -> str:
    tokens = THEMES.get(theme, THEMES[DEFAULT_THEME])
    return _TEMPLATE.format(**tokens)
