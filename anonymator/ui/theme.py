DEFAULT_THEME = "cuma"

THEMES = {
    "cuma": {"primary": "#31B700", "action": "#00965E", "dark": "#063b27",
             "accent": "#E8621A", "bg": "#FFFFFF", "text": "#10331F",
             "bg_hero": "#E8F3EA", "surface": "#FFFFFF", "surface_alt": "#F3FAF4",
             "border": "#E2E8E4", "text_muted": "#6B7C72",
             "info": "#4FA8D8", "info_hover": "#3D93C2"},
    "cap":  {"primary": "#1DA8E2", "action": "#1570B8", "dark": "#0D1A35",
             "accent": "#E8621A", "bg": "#FFFFFF", "text": "#1E1E2E",
             "bg_hero": "#EAF4FB", "surface": "#FFFFFF", "surface_alt": "#F4F9FD",
             "border": "#E1E8EF", "text_muted": "#6B7280",
             "info": "#5BBCEC", "info_hover": "#3FA3D6"},
}

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
"""


def build_qss(theme: str) -> str:
    tokens = THEMES.get(theme, THEMES[DEFAULT_THEME])
    return _TEMPLATE.format(**tokens)
