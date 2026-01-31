"""
Visual Templates - Szablony wizualne dla grafik
- Definicje kolorów i stylów
- Predefiniowane layouty
- Brand palettes
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from enum import Enum


class AspectRatio(Enum):
    """Proporcje obrazu dla różnych platform"""
    LINKEDIN_POST = (1200, 630)      # 1.91:1
    LINKEDIN_SQUARE = (1200, 1200)   # 1:1
    INSTAGRAM_SQUARE = (1080, 1080)  # 1:1
    INSTAGRAM_PORTRAIT = (1080, 1350) # 4:5
    INSTAGRAM_STORY = (1080, 1920)   # 9:16
    TWITTER_POST = (1200, 675)       # 16:9
    FACEBOOK_POST = (1200, 630)      # 1.91:1
    FACEBOOK_SQUARE = (1200, 1200)   # 1:1
    CAROUSEL_SLIDE = (1080, 1080)    # 1:1


@dataclass
class ColorPalette:
    """Paleta kolorów"""
    name: str
    primary: str           # Główny kolor
    secondary: str         # Drugi kolor
    background: str        # Tło
    surface: str           # Powierzchnie (karty)
    text_primary: str      # Główny tekst
    text_secondary: str    # Drugi tekst
    accent: str            # Akcent
    gradient_start: str = ""
    gradient_end: str = ""
    
    def __post_init__(self):
        if not self.gradient_start:
            self.gradient_start = self.primary
        if not self.gradient_end:
            self.gradient_end = self.secondary


# === PREDEFINIOWANE PALETY ===

PALETTES: Dict[str, ColorPalette] = {
    "dark_professional": ColorPalette(
        name="Dark Professional",
        primary="#3B82F6",      # Blue
        secondary="#8B5CF6",    # Purple
        background="#0F172A",   # Dark slate
        surface="#1E293B",      # Slate
        text_primary="#F8FAFC", # White
        text_secondary="#94A3B8", # Gray
        accent="#22D3EE",       # Cyan
        gradient_start="#3B82F6",
        gradient_end="#8B5CF6"
    ),
    
    "dark_minimal": ColorPalette(
        name="Dark Minimal",
        primary="#FFFFFF",
        secondary="#A1A1AA",
        background="#09090B",   # Zinc 950
        surface="#18181B",      # Zinc 900
        text_primary="#FAFAFA",
        text_secondary="#71717A",
        accent="#FFFFFF",
        gradient_start="#27272A",
        gradient_end="#09090B"
    ),
    
    "light_clean": ColorPalette(
        name="Light Clean",
        primary="#1E40AF",      # Blue 800
        secondary="#3B82F6",    # Blue 500
        background="#FFFFFF",
        surface="#F8FAFC",
        text_primary="#0F172A",
        text_secondary="#64748B",
        accent="#2563EB",
        gradient_start="#EFF6FF",
        gradient_end="#FFFFFF"
    ),
    
    "gradient_sunset": ColorPalette(
        name="Gradient Sunset",
        primary="#F97316",      # Orange
        secondary="#EC4899",    # Pink
        background="#0F172A",
        surface="#1E293B",
        text_primary="#FFFFFF",
        text_secondary="#CBD5E1",
        accent="#FCD34D",
        gradient_start="#F97316",
        gradient_end="#EC4899"
    ),
    
    "gradient_ocean": ColorPalette(
        name="Gradient Ocean",
        primary="#06B6D4",      # Cyan
        secondary="#3B82F6",    # Blue
        background="#0C1222",
        surface="#162032",
        text_primary="#F0F9FF",
        text_secondary="#7DD3FC",
        accent="#22D3EE",
        gradient_start="#06B6D4",
        gradient_end="#3B82F6"
    ),
    
    "neon_tech": ColorPalette(
        name="Neon Tech",
        primary="#00FF88",      # Neon green
        secondary="#00D4FF",    # Neon blue
        background="#0A0A0A",
        surface="#141414",
        text_primary="#FFFFFF",
        text_secondary="#888888",
        accent="#FF00FF",
        gradient_start="#00FF88",
        gradient_end="#00D4FF"
    ),
    
    "warm_earth": ColorPalette(
        name="Warm Earth",
        primary="#D97706",      # Amber
        secondary="#92400E",    # Brown
        background="#1C1917",   # Stone 900
        surface="#292524",      # Stone 800
        text_primary="#FAFAF9",
        text_secondary="#A8A29E",
        accent="#FBBF24",
        gradient_start="#D97706",
        gradient_end="#92400E"
    ),
    
    "corporate_blue": ColorPalette(
        name="Corporate Blue",
        primary="#1E3A8A",      # Blue 900
        secondary="#1E40AF",    # Blue 800
        background="#FFFFFF",
        surface="#F1F5F9",
        text_primary="#0F172A",
        text_secondary="#475569",
        accent="#3B82F6",
        gradient_start="#1E3A8A",
        gradient_end="#3B82F6"
    )
}


@dataclass
class TypographyStyle:
    """Styl typografii"""
    headline_size: int = 72
    subheadline_size: int = 36
    body_size: int = 24
    caption_size: int = 18
    
    headline_weight: str = "bold"
    line_height_ratio: float = 1.2
    letter_spacing: int = 0
    
    max_chars_per_line: int = 25


@dataclass  
class LayoutConfig:
    """Konfiguracja layoutu"""
    padding: int = 80
    margin: int = 40
    
    # Pozycje elementów (relative 0-1)
    headline_y: float = 0.35      # 35% od góry
    subheadline_y: float = 0.55   # 55% od góry
    footer_y: float = 0.90        # 90% od góry
    
    # Wyrównanie
    text_align: str = "left"  # left, center, right
    
    # Dekoracje
    show_grid: bool = False
    show_accent_line: bool = True
    accent_line_width: int = 4


@dataclass
class VisualTemplate:
    """Kompletny szablon wizualny"""
    name: str
    description: str
    palette: ColorPalette
    typography: TypographyStyle
    layout: LayoutConfig
    aspect_ratio: AspectRatio = AspectRatio.LINKEDIN_POST
    
    # Efekty
    use_gradient_bg: bool = False
    use_pattern: bool = True
    pattern_type: str = "grid"  # grid, dots, lines, none
    pattern_opacity: float = 0.1
    
    # Logo/branding
    show_logo: bool = False
    logo_position: str = "bottom_right"  # top_left, top_right, bottom_left, bottom_right


# === PREDEFINIOWANE SZABLONY ===

VISUAL_TEMPLATES: Dict[str, VisualTemplate] = {
    "tech_dark": VisualTemplate(
        name="Tech Dark",
        description="Ciemny, techniczny styl dla IT/dev",
        palette=PALETTES["dark_professional"],
        typography=TypographyStyle(
            headline_size=80,
            max_chars_per_line=20
        ),
        layout=LayoutConfig(
            padding=100,
            show_grid=True,
            show_accent_line=True
        ),
        use_pattern=True,
        pattern_type="grid"
    ),
    
    "minimal_dark": VisualTemplate(
        name="Minimal Dark",
        description="Minimalistyczny ciemny styl",
        palette=PALETTES["dark_minimal"],
        typography=TypographyStyle(
            headline_size=90,
            max_chars_per_line=18
        ),
        layout=LayoutConfig(
            padding=120,
            text_align="center",
            show_grid=False,
            show_accent_line=False
        ),
        use_pattern=False
    ),
    
    "gradient_bold": VisualTemplate(
        name="Gradient Bold",
        description="Gradient z dużą typografią",
        palette=PALETTES["gradient_sunset"],
        typography=TypographyStyle(
            headline_size=85,
            max_chars_per_line=16
        ),
        layout=LayoutConfig(
            padding=100,
            text_align="left",
            show_accent_line=True
        ),
        use_gradient_bg=True,
        use_pattern=False
    ),
    
    "corporate_clean": VisualTemplate(
        name="Corporate Clean",
        description="Profesjonalny, jasny styl",
        palette=PALETTES["corporate_blue"],
        typography=TypographyStyle(
            headline_size=70,
            max_chars_per_line=22
        ),
        layout=LayoutConfig(
            padding=80,
            text_align="left"
        ),
        use_pattern=True,
        pattern_type="dots",
        pattern_opacity=0.05
    ),
    
    "neon_statement": VisualTemplate(
        name="Neon Statement",
        description="Neonowy, attention-grabbing",
        palette=PALETTES["neon_tech"],
        typography=TypographyStyle(
            headline_size=75,
            max_chars_per_line=18
        ),
        layout=LayoutConfig(
            padding=90,
            show_accent_line=True,
            accent_line_width=6
        ),
        use_pattern=True,
        pattern_type="lines"
    ),
    
    "instagram_story": VisualTemplate(
        name="Instagram Story",
        description="Pionowy format na Stories",
        palette=PALETTES["gradient_ocean"],
        typography=TypographyStyle(
            headline_size=65,
            max_chars_per_line=14
        ),
        layout=LayoutConfig(
            padding=60,
            headline_y=0.40,
            text_align="center"
        ),
        aspect_ratio=AspectRatio.INSTAGRAM_STORY,
        use_gradient_bg=True
    ),
    
    "carousel_slide": VisualTemplate(
        name="Carousel Slide",
        description="Slajd do karuzeli",
        palette=PALETTES["dark_professional"],
        typography=TypographyStyle(
            headline_size=60,
            subheadline_size=32,
            max_chars_per_line=20
        ),
        layout=LayoutConfig(
            padding=70,
            headline_y=0.30,
            subheadline_y=0.50,
            text_align="center"
        ),
        aspect_ratio=AspectRatio.CAROUSEL_SLIDE,
        use_pattern=True
    )
}


# === HELPER FUNCTIONS ===

def get_template(name: str) -> Optional[VisualTemplate]:
    """Pobiera szablon po nazwie"""
    return VISUAL_TEMPLATES.get(name)


def get_palette(name: str) -> Optional[ColorPalette]:
    """Pobiera paletę po nazwie"""
    return PALETTES.get(name)


def list_templates() -> List[str]:
    """Lista dostępnych szablonów"""
    return list(VISUAL_TEMPLATES.keys())


def list_palettes() -> List[str]:
    """Lista dostępnych palet"""
    return list(PALETTES.keys())


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Konwertuje hex na RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Konwertuje RGB na hex"""
    return f"#{r:02x}{g:02x}{b:02x}"


def create_custom_palette(
    name: str,
    primary: str,
    background: str,
    text: str,
    accent: str = None
) -> ColorPalette:
    """Tworzy niestandardową paletę"""
    return ColorPalette(
        name=name,
        primary=primary,
        secondary=accent or primary,
        background=background,
        surface=background,
        text_primary=text,
        text_secondary=text,
        accent=accent or primary
    )


# === TEST ===
if __name__ == "__main__":
    print("=== Visual Templates ===\n")
    
    print("Available Templates:")
    for name, template in VISUAL_TEMPLATES.items():
        print(f"  • {name}: {template.description}")
    
    print("\nAvailable Palettes:")
    for name, palette in PALETTES.items():
        print(f"  • {name}: {palette.primary} / {palette.background}")
    
    print("\nAspect Ratios:")
    for ratio in AspectRatio:
        print(f"  • {ratio.name}: {ratio.value}")