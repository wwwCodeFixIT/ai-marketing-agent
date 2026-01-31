"""
Card Generator - Profesjonalny generator grafik
- Zaawansowana typografia
- Efekty wizualne
- Wiele stylów kart
"""

import io
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
import math

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from .templates import (
    VisualTemplate,
    ColorPalette,
    AspectRatio,
    VISUAL_TEMPLATES,
    PALETTES,
    hex_to_rgb,
    get_template
)

logger = logging.getLogger(__name__)

FONTS_DIR = Path(__file__).parent.parent / "fonts"
FONTS_DIR.mkdir(exist_ok=True)


@dataclass
class GraphicCard:
    """Wygenerowana grafika"""
    image: Image.Image
    width: int
    height: int
    template_name: str

    def save(self, path: str, format: str = "PNG", quality: int = 95):
        self.image.save(path, format=format, quality=quality)

    def to_bytes(self, format: str = "PNG") -> bytes:
        buffer = io.BytesIO()
        self.image.save(buffer, format=format)
        return buffer.getvalue()

    def resize(self, new_size: Tuple[int, int]) -> 'GraphicCard':
        resized = self.image.resize(new_size, Image.Resampling.LANCZOS)
        return GraphicCard(
            image=resized,
            width=new_size[0],
            height=new_size[1],
            template_name=self.template_name
        )
    
    def get_thumbnail(self, max_size: int = 400) -> Image.Image:
        """Zwraca miniaturkę do podglądu"""
        ratio = min(max_size / self.width, max_size / self.height)
        new_size = (int(self.width * ratio), int(self.height * ratio))
        return self.image.resize(new_size, Image.Resampling.LANCZOS)


class FontManager:
    """Zarządza fontami z fallbackami"""
    
    SYSTEM_FONTS_BOLD = [
        "arialbd.ttf", "Arial Bold", "Arial-Bold",
        "Helvetica-Bold", "DejaVuSans-Bold.ttf",
        "segoeui.ttf", "Segoe UI Bold"
    ]
    
    SYSTEM_FONTS_REGULAR = [
        "arial.ttf", "Arial", "Helvetica",
        "DejaVuSans.ttf", "segoeui.ttf", "Segoe UI"
    ]

    def __init__(self):
        self.fonts_cache = {}

    def get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        cache_key = f"{'bold' if bold else 'regular'}_{size}"
        if cache_key in self.fonts_cache:
            return self.fonts_cache[cache_key]
        font = self._load_font(size, bold)
        self.fonts_cache[cache_key] = font
        return font

    def _load_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        font_list = self.SYSTEM_FONTS_BOLD if bold else self.SYSTEM_FONTS_REGULAR
        
        # Próbuj lokalne fonty
        local_names = ["Inter-Bold.ttf", "Roboto-Bold.ttf"] if bold else ["Inter-Regular.ttf", "Roboto-Regular.ttf"]
        for name in local_names:
            font_path = FONTS_DIR / name
            if font_path.exists():
                try:
                    return ImageFont.truetype(str(font_path), size)
                except:
                    pass
        
        # Próbuj systemowe
        for font_name in font_list:
            try:
                return ImageFont.truetype(font_name, size)
            except:
                continue
        
        # Fallback
        try:
            return ImageFont.load_default().font_variant(size=size)
        except:
            return ImageFont.load_default()


class GraphicsEngine:
    """
    Główny silnik graficzny z zaawansowanymi efektami.
    """
    
    def __init__(self):
        self.font_manager = FontManager()

    def _hex_to_rgba(self, hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
        """Konwertuje hex na RGBA"""
        r, g, b = hex_to_rgb(hex_color)
        return (r, g, b, alpha)

    def _create_gradient(
        self, 
        width: int, 
        height: int, 
        color_start: str, 
        color_end: str,
        direction: str = "diagonal"
    ) -> Image.Image:
        """Tworzy płynny gradient"""
        base = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(base)
        
        r1, g1, b1 = hex_to_rgb(color_start)
        r2, g2, b2 = hex_to_rgb(color_end)
        
        if direction == "vertical":
            for y in range(height):
                ratio = y / height
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        elif direction == "horizontal":
            for x in range(width):
                ratio = x / width
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)
                draw.line([(x, 0), (x, height)], fill=(r, g, b))
        
        elif direction == "radial":
            # Gradient radialny od środka
            center_x, center_y = width // 2, height // 2
            max_dist = math.sqrt(center_x**2 + center_y**2)
            
            for y in range(height):
                for x in range(width):
                    dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                    ratio = min(dist / max_dist, 1.0)
                    r = int(r1 + (r2 - r1) * ratio)
                    g = int(g1 + (g2 - g1) * ratio)
                    b = int(b1 + (b2 - b1) * ratio)
                    draw.point((x, y), fill=(r, g, b))
        
        else:  # diagonal
            for y in range(height):
                for x in range(width):
                    ratio = (x / width * 0.5) + (y / height * 0.5)
                    r = int(r1 + (r2 - r1) * ratio)
                    g = int(g1 + (g2 - g1) * ratio)
                    b = int(b1 + (b2 - b1) * ratio)
                    draw.point((x, y), fill=(r, g, b))
        
        return base

    def _add_noise(self, img: Image.Image, intensity: float = 0.03) -> Image.Image:
        """Dodaje subtelny szum dla bardziej naturalnego wyglądu"""
        import random
        
        pixels = img.load()
        width, height = img.size
        
        for y in range(height):
            for x in range(width):
                if random.random() < intensity:
                    r, g, b = pixels[x, y][:3] if len(pixels[x, y]) > 3 else pixels[x, y]
                    noise = random.randint(-15, 15)
                    r = max(0, min(255, r + noise))
                    g = max(0, min(255, g + noise))
                    b = max(0, min(255, b + noise))
                    pixels[x, y] = (r, g, b)
        
        return img

    def _draw_pattern(
        self,
        img: Image.Image,
        pattern_type: str,
        color: str,
        opacity: float = 0.1
    ) -> Image.Image:
        """Rysuje wzór z przezroczystością"""
        width, height = img.size
        
        # Utwórz warstwę wzoru
        pattern_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pattern_layer)
        
        r, g, b = hex_to_rgb(color)
        alpha = int(255 * opacity)
        pattern_color = (r, g, b, alpha)
        
        if pattern_type == "grid":
            spacing = 50
            for x in range(0, width, spacing):
                draw.line([(x, 0), (x, height)], fill=pattern_color, width=1)
            for y in range(0, height, spacing):
                draw.line([(0, y), (width, y)], fill=pattern_color, width=1)
        
        elif pattern_type == "dots":
            spacing = 40
            radius = 2
            for x in range(spacing, width, spacing):
                for y in range(spacing, height, spacing):
                    draw.ellipse(
                        [x - radius, y - radius, x + radius, y + radius],
                        fill=pattern_color
                    )
        
        elif pattern_type == "lines":
            spacing = 60
            for i in range(-height, width + height, spacing):
                draw.line([(i, 0), (i + height, height)], fill=pattern_color, width=1)
        
        elif pattern_type == "circles":
            for i in range(3):
                radius = 150 + i * 100
                cx, cy = width - 150, height - 150
                draw.ellipse(
                    [cx - radius, cy - radius, cx + radius, cy + radius],
                    outline=pattern_color,
                    width=2
                )
        
        # Połącz warstwy
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        return Image.alpha_composite(img, pattern_layer)

    def _draw_glow(
        self,
        img: Image.Image,
        position: Tuple[int, int],
        radius: int,
        color: str,
        intensity: float = 0.3
    ) -> Image.Image:
        """Dodaje efekt glow"""
        width, height = img.size
        glow_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow_layer)
        
        r, g, b = hex_to_rgb(color)
        x, y = position
        
        # Rysuj gradient koła
        for i in range(radius, 0, -5):
            alpha = int(255 * intensity * (1 - i / radius))
            draw.ellipse(
                [x - i, y - i, x + i, y + i],
                fill=(r, g, b, alpha)
            )
        
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        return Image.alpha_composite(img, glow_layer)

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Inteligentne łamanie tekstu"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            line_width = bbox[2] - bbox[0]
            
            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

    def _draw_text_with_effects(
        self,
        draw: ImageDraw.Draw,
        text: str,
        position: Tuple[int, int],
        font: ImageFont.FreeTypeFont,
        fill: str,
        shadow: bool = True,
        shadow_offset: int = 4,
        shadow_blur: bool = False,
        outline: bool = False,
        outline_color: str = "#000000",
        outline_width: int = 2
    ):
        """Rysuje tekst z efektami"""
        x, y = position
        
        # Outline (obrys)
        if outline:
            for ox in range(-outline_width, outline_width + 1):
                for oy in range(-outline_width, outline_width + 1):
                    if ox != 0 or oy != 0:
                        draw.text((x + ox, y + oy), text, font=font, fill=outline_color)
        
        # Cień
        if shadow:
            shadow_color = "#000000"
            # Wielowarstwowy cień dla miękkości
            for i in range(3):
                offset = shadow_offset - i
                alpha_hex = hex(int(255 * (0.3 - i * 0.1)))[2:].zfill(2)
                draw.text(
                    (x + offset, y + offset),
                    text,
                    font=font,
                    fill=shadow_color
                )
        
        # Główny tekst
        draw.text(position, text, font=font, fill=fill)

    def _add_vignette(self, img: Image.Image, intensity: float = 0.3) -> Image.Image:
        """Dodaje efekt winiety"""
        width, height = img.size
        
        # Utwórz maskę winiety
        vignette = Image.new('L', (width, height), 255)
        draw = ImageDraw.Draw(vignette)
        
        # Gradient od centrum do krawędzi
        center_x, center_y = width // 2, height // 2
        max_dist = math.sqrt(center_x**2 + center_y**2)
        
        for y in range(height):
            for x in range(width):
                dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                ratio = dist / max_dist
                # Stosuj winietę tylko na krawędziach
                if ratio > 0.5:
                    darkness = int(255 * (1 - (ratio - 0.5) * 2 * intensity))
                    vignette.putpixel((x, y), max(0, darkness))
        
        # Zastosuj winietę
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Blur winiety dla miękkości
        vignette = vignette.filter(ImageFilter.GaussianBlur(radius=50))
        
        # Połącz
        result = Image.composite(img, Image.new('RGB', img.size, (0, 0, 0)), vignette)
        
        return result

    def create_card(
        self,
        headline: str,
        template: VisualTemplate = None,
        template_name: str = "tech_dark",
        subheadline: str = "",
        author: str = "",
        custom_palette: ColorPalette = None,
        add_effects: bool = True
    ) -> GraphicCard:
        """
        Tworzy profesjonalną kartę graficzną.
        """
        
        # Pobierz szablon
        if template is None:
            template = get_template(template_name)
            if template is None:
                template = list(VISUAL_TEMPLATES.values())[0]
        
        palette = custom_palette or template.palette
        width, height = template.aspect_ratio.value
        
        # === TŁO ===
        if template.use_gradient_bg:
            img = self._create_gradient(
                width, height,
                palette.gradient_start,
                palette.gradient_end,
                "diagonal"
            )
        else:
            img = Image.new('RGB', (width, height), palette.background)
        
        # Konwertuj do RGBA dla efektów
        img = img.convert('RGBA')
        
        # === WZORY ===
        if template.use_pattern and template.pattern_type != "none":
            img = self._draw_pattern(
                img,
                template.pattern_type,
                palette.surface,
                template.pattern_opacity
            )
        
        # === EFEKT GLOW ===
        if add_effects:
            # Glow w rogu
            img = self._draw_glow(
                img,
                (width - 200, 200),
                300,
                palette.accent,
                0.15
            )
        
        draw = ImageDraw.Draw(img)
        
        # === PARAMETRY LAYOUTU ===
        padding = template.layout.padding
        content_width = width - (padding * 2)
        
        # === LINIA AKCENTOWA ===
        if template.layout.show_accent_line:
            accent_y = int(height * template.layout.headline_y) - 60
            # Gradient w linii akcentowej
            for i in range(120):
                alpha = int(255 * (1 - i / 120))
                r, g, b = hex_to_rgb(palette.accent)
                draw.line(
                    [(padding + i, accent_y), (padding + i, accent_y + template.layout.accent_line_width)],
                    fill=(r, g, b, alpha)
                )
        
        # === HEADLINE ===
        font_headline = self.font_manager.get_font(
            template.typography.headline_size,
            bold=True
        )
        
        headline_text = headline.upper()
        lines = self._wrap_text(headline_text, font_headline, content_width)
        
        line_height = int(template.typography.headline_size * template.typography.line_height_ratio)
        total_text_height = len(lines) * line_height
        
        start_y = int(height * template.layout.headline_y) - (total_text_height // 2)
        
        current_y = start_y
        for line in lines:
            bbox = font_headline.getbbox(line)
            line_width = bbox[2] - bbox[0]
            
            if template.layout.text_align == "center":
                x = (width - line_width) // 2
            elif template.layout.text_align == "right":
                x = width - padding - line_width
            else:
                x = padding
            
            self._draw_text_with_effects(
                draw,
                line,
                (x, current_y),
                font_headline,
                palette.text_primary,
                shadow=True,
                shadow_offset=5
            )
            current_y += line_height
        
        # === SUBHEADLINE ===
        if subheadline:
            font_sub = self.font_manager.get_font(
                template.typography.subheadline_size,
                bold=False
            )
            sub_y = int(height * template.layout.subheadline_y)
            
            bbox = font_sub.getbbox(subheadline)
            sub_width = bbox[2] - bbox[0]
            
            if template.layout.text_align == "center":
                sub_x = (width - sub_width) // 2
            else:
                sub_x = padding
            
            draw.text(
                (sub_x, sub_y),
                subheadline,
                font=font_sub,
                fill=palette.text_secondary
            )
        
        # === STOPKA ===
        if author:
            font_footer = self.font_manager.get_font(
                template.typography.caption_size,
                bold=False
            )
            footer_y = int(height * template.layout.footer_y)
            footer_text = f"@{author.lstrip('@')}  •  INSIGHTS"
            
            # Tło pod stopką
            footer_bbox = font_footer.getbbox(footer_text)
            footer_width = footer_bbox[2] - footer_bbox[0]
            
            draw.rounded_rectangle(
                [padding - 15, footer_y - 8, padding + footer_width + 15, footer_y + footer_bbox[3] + 8],
                radius=20,
                fill=(*hex_to_rgb(palette.surface), 180)
            )
            
            draw.text(
                (padding, footer_y),
                footer_text,
                font=font_footer,
                fill=palette.text_secondary
            )
        
        # === WINIETA ===
        if add_effects:
            img = img.convert('RGB')
            img = self._add_vignette(img, 0.2)
        else:
            img = img.convert('RGB')
        
        return GraphicCard(
            image=img,
            width=width,
            height=height,
            template_name=template.name
        )

    def create_quote_card(
        self,
        quote: str,
        author: str,
        template_name: str = "minimal_dark",
        add_effects: bool = True
    ) -> GraphicCard:
        """Tworzy elegancką kartę z cytatem"""
        
        template = get_template(template_name) or list(VISUAL_TEMPLATES.values())[0]
        palette = template.palette
        width, height = template.aspect_ratio.value
        
        # Tło
        img = Image.new('RGBA', (width, height), (*hex_to_rgb(palette.background), 255))
        
        # Subtelny gradient overlay
        gradient = self._create_gradient(width, height, palette.background, palette.surface, "radial")
        gradient = gradient.convert('RGBA')
        img = Image.blend(img.convert('RGBA'), gradient.convert('RGBA'), 0.3)
        
        draw = ImageDraw.Draw(img)
        padding = 100
        
        # Duży cudzysłów ozdobny
        font_quote_mark = self.font_manager.get_font(200, bold=True)
        r, g, b = hex_to_rgb(palette.accent)
        draw.text(
            (padding - 20, 40),
            '"',
            font=font_quote_mark,
            fill=(r, g, b, 100)
        )
        
        # Cytat
        font_quote = self.font_manager.get_font(44, bold=False)
        lines = self._wrap_text(quote, font_quote, width - padding * 2 - 40)
        
        y = 180
        for line in lines:
            draw.text(
                (padding + 20, y),
                line,
                font=font_quote,
                fill=palette.text_primary
            )
            y += 60
        
        # Linia dekoracyjna
        draw.line(
            [(padding + 20, y + 20), (padding + 100, y + 20)],
            fill=palette.accent,
            width=3
        )
        
        # Autor
        font_author = self.font_manager.get_font(28, bold=True)
        draw.text(
            (padding + 20, y + 40),
            f"— {author}",
            font=font_author,
            fill=palette.text_secondary
        )
        
        img = img.convert('RGB')
        
        if add_effects:
            img = self._add_vignette(img, 0.15)
        
        return GraphicCard(
            image=img,
            width=width,
            height=height,
            template_name="quote"
        )

    def create_stats_card(
        self,
        stat_value: str,
        stat_label: str,
        description: str = "",
        template_name: str = "gradient_bold",
        add_effects: bool = True
    ) -> GraphicCard:
        """Tworzy kartę ze statystyką z efektami"""
        
        template = get_template(template_name) or list(VISUAL_TEMPLATES.values())[0]
        palette = template.palette
        width, height = template.aspect_ratio.value
        
        # Gradient tło
        img = self._create_gradient(
            width, height,
            palette.gradient_start,
            palette.gradient_end,
            "diagonal"
        )
        img = img.convert('RGBA')
        
        # Dodaj kółka dekoracyjne
        img = self._draw_pattern(img, "circles", palette.text_primary, 0.05)
        
        # Glow za statystyką
        img = self._draw_glow(img, (width // 2, height // 2 - 50), 250, palette.accent, 0.2)
        
        draw = ImageDraw.Draw(img)
        
        # Statystyka
        font_stat = self.font_manager.get_font(180, bold=True)
        bbox = font_stat.getbbox(stat_value)
        stat_width = bbox[2] - bbox[0]
        stat_height = bbox[3] - bbox[1]
        stat_x = (width - stat_width) // 2
        stat_y = (height - stat_height) // 2 - 80
        
        self._draw_text_with_effects(
            draw,
            stat_value,
            (stat_x, stat_y),
            font_stat,
            palette.text_primary,
            shadow=True,
            shadow_offset=8
        )
        
        # Label
        font_label = self.font_manager.get_font(36, bold=True)
        label_text = stat_label.upper()
        bbox = font_label.getbbox(label_text)
        label_width = bbox[2] - bbox[0]
        label_x = (width - label_width) // 2
        
        draw.text(
            (label_x, stat_y + stat_height + 40),
            label_text,
            font=font_label,
            fill=palette.text_primary
        )
        
        # Opis
        if description:
            font_desc = self.font_manager.get_font(24, bold=False)
            lines = self._wrap_text(description, font_desc, width - 200)
            y = stat_y + stat_height + 100
            for line in lines:
                bbox = font_desc.getbbox(line)
                line_width = bbox[2] - bbox[0]
                line_x = (width - line_width) // 2
                draw.text(
                    (line_x, y),
                    line,
                    font=font_desc,
                    fill=palette.text_secondary
                )
                y += 35
        
        img = img.convert('RGB')
        
        if add_effects:
            img = self._add_vignette(img, 0.25)
        
        return GraphicCard(
            image=img,
            width=width,
            height=height,
            template_name="stats"
        )

    def create_list_card(
        self,
        title: str,
        items: List[str],
        template_name: str = "tech_dark",
        add_effects: bool = True
    ) -> GraphicCard:
        """Tworzy kartę z listą punktów"""
        
        template = get_template(template_name) or list(VISUAL_TEMPLATES.values())[0]
        palette = template.palette
        width, height = template.aspect_ratio.value
        
        # Tło
        if template.use_gradient_bg:
            img = self._create_gradient(width, height, palette.gradient_start, palette.gradient_end)
        else:
            img = Image.new('RGB', (width, height), palette.background)
        
        img = img.convert('RGBA')
        
        if template.use_pattern:
            img = self._draw_pattern(img, template.pattern_type, palette.surface, 0.08)
        
        draw = ImageDraw.Draw(img)
        padding = 80
        
        # Tytuł
        font_title = self.font_manager.get_font(56, bold=True)
        self._draw_text_with_effects(
            draw,
            title.upper(),
            (padding, 60),
            font_title,
            palette.text_primary,
            shadow=True
        )
        
        # Linia pod tytułem
        draw.rectangle(
            [padding, 140, padding + 80, 144],
            fill=palette.accent
        )
        
        # Lista
        font_item = self.font_manager.get_font(32, bold=False)
        font_number = self.font_manager.get_font(28, bold=True)
        
        y = 180
        for i, item in enumerate(items[:6], 1):  # Max 6 items
            # Numer
            number_text = f"{i:02d}"
            r, g, b = hex_to_rgb(palette.accent)
            
            # Kółko z numerem
            draw.ellipse(
                [padding, y, padding + 45, y + 45],
                fill=(r, g, b, 200)
            )
            
            # Numer w kółku
            num_bbox = font_number.getbbox(number_text)
            num_x = padding + (45 - (num_bbox[2] - num_bbox[0])) // 2
            num_y = y + (45 - (num_bbox[3] - num_bbox[1])) // 2 - 3
            draw.text(
                (num_x, num_y),
                number_text,
                font=font_number,
                fill=palette.background
            )
            
            # Tekst
            draw.text(
                (padding + 65, y + 8),
                item,
                font=font_item,
                fill=palette.text_primary
            )
            
            y += 70
        
        img = img.convert('RGB')
        
        if add_effects:
            img = self._add_vignette(img, 0.2)
        
        return GraphicCard(
            image=img,
            width=width,
            height=height,
            template_name="list"
        )

    def create_carousel(
        self,
        slides_content: List[Dict[str, str]],
        template_name: str = "carousel_slide"
    ) -> List[GraphicCard]:
        """Tworzy karuzelę slajdów"""
        cards = []
        total = len(slides_content)
        
        for i, slide in enumerate(slides_content):
            headline = slide.get("headline", "")
            subheadline = slide.get("subheadline", "")
            
            card = self.create_card(
                headline=headline,
                template_name=template_name,
                subheadline=subheadline,
                author=f"{i+1}/{total}",
                add_effects=True
            )
            cards.append(card)
        
        return cards

    def export_for_platform(self, card: GraphicCard, platform: str) -> Dict[str, GraphicCard]:
        """Eksportuje w formatach dla platformy"""
        exports = {}
        platform = platform.lower()
        
        if platform == "linkedin":
            exports["post"] = card.resize(AspectRatio.LINKEDIN_POST.value)
            exports["square"] = card.resize(AspectRatio.LINKEDIN_SQUARE.value)
        elif platform == "instagram":
            exports["square"] = card.resize(AspectRatio.INSTAGRAM_SQUARE.value)
            exports["portrait"] = card.resize(AspectRatio.INSTAGRAM_PORTRAIT.value)
            exports["story"] = card.resize(AspectRatio.INSTAGRAM_STORY.value)
        elif platform == "twitter":
            exports["post"] = card.resize(AspectRatio.TWITTER_POST.value)
        elif platform == "facebook":
            exports["post"] = card.resize(AspectRatio.FACEBOOK_POST.value)
            exports["square"] = card.resize(AspectRatio.FACEBOOK_SQUARE.value)
        else:
            exports["original"] = card
        
        return exports


def create_quick_card(headline: str, style: str = "dark") -> GraphicCard:
    """Szybkie tworzenie karty"""
    engine = GraphicsEngine()
    template_name = "tech_dark" if style == "dark" else "corporate_clean"
    return engine.create_card(headline, template_name=template_name)