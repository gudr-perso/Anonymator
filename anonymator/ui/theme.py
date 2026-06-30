DEFAULT_THEME = "cuma"

THEMES = {
    "cuma": {"primary": "#31B700", "action": "#00965E", "dark": "#063b27",
             "accent": "#93C90E", "bg": "#F3FAF4", "text": "#10331f"},
    "cap":  {"primary": "#1DA8E2", "action": "#1570B8", "dark": "#0D1A35",
             "accent": "#E8621A", "bg": "#FFFFFF", "text": "#1E1E2E"},
}

_TEMPLATE = """
QWidget {{ background: {bg}; color: {text};
          font-family: 'Inter','Segoe UI',sans-serif; font-size: 14px; }}
QLabel#title {{ font-family: 'Space Grotesk','Segoe UI',sans-serif;
               font-size: 22px; font-weight: 700; color: {dark}; }}
QPushButton {{ background: {action}; color: white; border: none;
              border-radius: 6px; padding: 8px 16px; font-weight: 600; }}
QPushButton:hover {{ background: {primary}; }}
QPushButton#accent {{ background: {accent}; }}
QPushButton#ghost {{ background: transparent; color: {action};
                    border: 1px solid {action}; }}
"""


def build_qss(theme: str) -> str:
    tokens = THEMES.get(theme, THEMES[DEFAULT_THEME])
    return _TEMPLATE.format(**tokens)
