"""
Shared theme definitions and stylesheet generation.
"""


APP_THEMES = {
    "Spotify Dark": {
        "bg_primary": "#121212",
        "bg_secondary": "#181818",
        "bg_sidebar": "#000000",
        "bg_hover": "#282828",
        "bg_selected": "#3e3e3e",
        "text_primary": "#ffffff",
        "text_secondary": "#b3b3b3",
        "accent": "#1db954",
        "accent_hover": "#1ed760",
        "player_bar": "#181818",
    },
    "Ocean Blue": {
        "bg_primary": "#0a1929",
        "bg_secondary": "#0d2137",
        "bg_sidebar": "#051320",
        "bg_hover": "#132f4c",
        "bg_selected": "#173a5e",
        "text_primary": "#ffffff",
        "text_secondary": "#b2bac2",
        "accent": "#5090d3",
        "accent_hover": "#66b2ff",
        "player_bar": "#0d2137",
    },
    "Sunset Orange": {
        "bg_primary": "#1a1a1a",
        "bg_secondary": "#242424",
        "bg_sidebar": "#0d0d0d",
        "bg_hover": "#333333",
        "bg_selected": "#404040",
        "text_primary": "#ffffff",
        "text_secondary": "#a0a0a0",
        "accent": "#ff6b35",
        "accent_hover": "#ff8c5a",
        "player_bar": "#242424",
    },
    "Forest Green": {
        "bg_primary": "#1a2420",
        "bg_secondary": "#212d28",
        "bg_sidebar": "#0f1613",
        "bg_hover": "#2a3b33",
        "bg_selected": "#344840",
        "text_primary": "#e8f5e9",
        "text_secondary": "#a5d6a7",
        "accent": "#4caf50",
        "accent_hover": "#66bb6a",
        "player_bar": "#212d28",
    },
    "Purple Haze": {
        "bg_primary": "#1a1625",
        "bg_secondary": "#231d30",
        "bg_sidebar": "#0f0c17",
        "bg_hover": "#2d2540",
        "bg_selected": "#3d3354",
        "text_primary": "#f3e5f5",
        "text_secondary": "#ce93d8",
        "accent": "#ab47bc",
        "accent_hover": "#ba68c8",
        "player_bar": "#231d30",
    },
    "Classic Dark": {
        "bg_primary": "#2d2d2d",
        "bg_secondary": "#383838",
        "bg_sidebar": "#1e1e1e",
        "bg_hover": "#454545",
        "bg_selected": "#525252",
        "text_primary": "#ffffff",
        "text_secondary": "#aaaaaa",
        "accent": "#ff5252",
        "accent_hover": "#ff7070",
        "player_bar": "#383838",
    },
    "Light Mode": {
        "bg_primary": "#ffffff",
        "bg_secondary": "#f5f5f5",
        "bg_sidebar": "#e8e8e8",
        "bg_hover": "#e0e0e0",
        "bg_selected": "#d0d0d0",
        "text_primary": "#1a1a1a",
        "text_secondary": "#666666",
        "accent": "#1db954",
        "accent_hover": "#1ed760",
        "player_bar": "#f5f5f5",
    },
}

DEFAULT_THEME = "Spotify Dark"


def generate_stylesheet(theme: dict) -> str:
    """Generate stylesheet from theme colors."""
    return f'''
QMainWindow, QWidget {{
    background-color: {theme["bg_primary"]};
    color: {theme["text_primary"]};
}}

QLabel {{
    color: {theme["text_primary"]};
}}

QLabel#secondaryLabel {{
    color: {theme["text_secondary"]};
}}

QLabel#sectionLabel {{
    color: {theme["text_secondary"]};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}}

QLabel#emptyStateTitle {{
    color: {theme["text_primary"]};
    font-size: 24px;
    font-weight: 700;
}}

QLabel#emptyStateBody {{
    color: {theme["text_secondary"]};
    font-size: 13px;
}}

QLabel#contentEyebrow {{
    color: {theme["accent"]};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}}

QLabel#contentTitle {{
    color: {theme["text_primary"]};
    font-size: 28px;
    font-weight: 700;
}}

QLabel#contentSubtitle {{
    color: {theme["text_secondary"]};
    font-size: 13px;
}}

QPushButton {{
    background-color: {theme["bg_hover"]};
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    color: {theme["text_primary"]};
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: {theme["bg_selected"]};
}}

QPushButton:pressed {{
    background-color: {theme["bg_selected"]};
}}

QPushButton#primaryButton {{
    background-color: {theme["accent"]};
    color: #000000;
}}

QPushButton#primaryButton:hover {{
    background-color: {theme["accent_hover"]};
}}

QPushButton#iconButton {{
    background-color: transparent;
    padding: 4px;
    border-radius: 16px;
}}

QPushButton#iconButton:hover {{
    background-color: rgba(255, 255, 255, 0.1);
}}

QPushButton#navButton {{
    text-align: left;
    padding: 10px 12px;
    border-radius: 8px;
    font-weight: 600;
    background-color: transparent;
    color: {theme["text_secondary"]};
}}

QPushButton#navButton:hover {{
    background-color: {theme["bg_hover"]};
    color: {theme["text_primary"]};
}}

QPushButton#navButton[active="true"] {{
    background-color: {theme["bg_hover"]};
    color: {theme["text_primary"]};
}}

QPushButton#subtleButton {{
    text-align: left;
    padding: 8px 10px;
    border-radius: 8px;
    font-weight: 600;
    background-color: {theme["bg_secondary"]};
    color: {theme["text_secondary"]};
}}

QPushButton#subtleButton:hover {{
    background-color: {theme["bg_hover"]};
    color: {theme["text_primary"]};
}}

QPushButton#transportButton {{
    background-color: transparent;
    border-radius: 18px;
    padding: 0;
}}

QPushButton#transportButton:hover {{
    background-color: {theme["bg_hover"]};
}}

QPushButton#playButton {{
    background-color: {theme["accent"]};
    border-radius: 22px;
    padding: 0;
}}

QPushButton#playButton:hover {{
    background-color: {theme["accent_hover"]};
}}

QPushButton#pillButton {{
    border-radius: 14px;
    padding: 6px 10px;
    background-color: {theme["bg_hover"]};
    color: {theme["text_secondary"]};
    font-size: 11px;
}}

QPushButton#pillButton:hover {{
    background-color: {theme["bg_selected"]};
    color: {theme["text_primary"]};
}}

QLineEdit {{
    background-color: {theme["bg_hover"]};
    border: none;
    border-radius: 20px;
    padding: 10px 16px;
    color: {theme["text_primary"]};
    selection-background-color: {theme["accent"]};
}}

QLineEdit:focus {{
    background-color: {theme["bg_selected"]};
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {theme["bg_selected"]};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {theme["text_primary"]};
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}

QSlider::handle:horizontal:hover {{
    background: {theme["accent"]};
}}

QSlider::sub-page:horizontal {{
    background: {theme["accent"]};
    border-radius: 2px;
}}

QListWidget, QTableWidget {{
    background-color: {theme["bg_primary"]};
    border: none;
    color: {theme["text_primary"]};
    outline: none;
}}

QListWidget::item, QTableWidget::item {{
    padding: 8px;
    border-radius: 4px;
}}

QListWidget::item:hover, QTableWidget::item:hover {{
    background-color: {theme["bg_hover"]};
}}

QListWidget::item:selected, QTableWidget::item:selected {{
    background-color: {theme["bg_selected"]};
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {theme["bg_selected"]};
    border-radius: 4px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {theme["text_secondary"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 8px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {theme["bg_selected"]};
    border-radius: 4px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {theme["text_secondary"]};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

QMenu {{
    background-color: {theme["bg_hover"]};
    border: 1px solid {theme["bg_selected"]};
    border-radius: 4px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 32px 8px 16px;
    border-radius: 2px;
}}

QMenu::item:selected {{
    background-color: {theme["bg_selected"]};
}}

QMenuBar {{
    background-color: {theme["bg_secondary"]};
    color: {theme["text_primary"]};
}}

QMenuBar::item:selected {{
    background-color: {theme["bg_hover"]};
}}

QHeaderView::section {{
    background-color: {theme["bg_primary"]};
    color: {theme["text_secondary"]};
    border: none;
    padding: 8px;
    font-weight: bold;
}}

QFrame#sidebar {{
    background-color: {theme["bg_sidebar"]};
}}

QFrame#playerBar {{
    background-color: {theme["player_bar"]};
    border-top: 1px solid {theme["bg_hover"]};
}}

QFrame#albumCard {{
    background-color: {theme["bg_secondary"]};
    border-radius: 14px;
    border: 1px solid transparent;
}}

QFrame#albumCard:hover {{
    background-color: {theme["bg_hover"]};
    border: 1px solid {theme["bg_selected"]};
}}

QWidget#sidebarContent {{
    background-color: {theme["bg_sidebar"]};
}}

QFrame#statsCard {{
    background-color: {theme["bg_secondary"]};
    border-radius: 12px;
    border: 1px solid {theme["bg_hover"]};
}}

QFrame#contentHeader {{
    background-color: {theme["bg_primary"]};
    border-bottom: 1px solid {theme["bg_hover"]};
}}

QFrame#albumHero {{
    background-color: {theme["bg_secondary"]};
    border-radius: 18px;
    border: 1px solid {theme["bg_hover"]};
}}

QInputDialog, QMessageBox, QDialog {{
    background-color: {theme["bg_secondary"]};
    color: {theme["text_primary"]};
}}

QProgressDialog {{
    background-color: {theme["bg_secondary"]};
    color: {theme["text_primary"]};
}}
'''


DEFAULT_STYLESHEET = generate_stylesheet(APP_THEMES[DEFAULT_THEME])
