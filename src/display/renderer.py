"""Drawing utilities and layout helpers for the e-ink display."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


class Renderer:
    """Helper class for drawing content on the display."""

    def __init__(self, width=250, height=122):
        self.width = width
        self.height = height
        self.image = None
        self.draw = None

    def create_canvas(self):
        """Create a new blank canvas."""
        self.image = Image.new('1', (self.width, self.height), 255)  # White background
        self.draw = ImageDraw.Draw(self.image)
        return self.image

    def get_font(self, size=12, bold=False):
        """
        Get a font for drawing text.

        Falls back to default font if custom fonts aren't available.
        """
        try:
            # Try to load DejaVu fonts (commonly available on Raspberry Pi)
            font_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
            font_path = f"/usr/share/fonts/truetype/dejavu/{font_name}"
            return ImageFont.truetype(font_path, size)
        except:
            # Fallback to default font
            return ImageFont.load_default()

    def draw_text(self, text, x, y, font_size=12, bold=False, anchor="lt"):
        """
        Draw text on the canvas.

        Args:
            text: Text to draw
            x, y: Position
            font_size: Font size in points
            bold: Use bold font
            anchor: Text anchor point (lt=left-top, mm=middle-middle, etc.)
        """
        font = self.get_font(font_size, bold)
        self.draw.text((x, y), text, font=font, fill=0, anchor=anchor)

    def draw_centered_text(self, text, y, font_size=12, bold=False):
        """Draw text centered horizontally at given y position."""
        self.draw_text(text, self.width // 2, y, font_size, bold, anchor="mt")

    def draw_line(self, x1, y1, x2, y2, width=1):
        """Draw a line."""
        self.draw.line([(x1, y1), (x2, y2)], fill=0, width=width)

    def draw_rectangle(self, x, y, width, height, fill=None, outline=0):
        """Draw a rectangle."""
        self.draw.rectangle(
            [(x, y), (x + width, y + height)],
            fill=fill,
            outline=outline
        )

    def draw_horizontal_line(self, y, thickness=1):
        """Draw a horizontal line across the entire width."""
        self.draw_line(0, y, self.width, y, thickness)

    def draw_vertical_line(self, x, thickness=1):
        """Draw a vertical line across the entire height."""
        self.draw_line(x, 0, x, self.height, thickness)

    def get_text_size(self, text, font_size=12, bold=False):
        """Get the bounding box size of text."""
        font = self.get_font(font_size, bold)
        bbox = self.draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def get_image(self):
        """Get the current image."""
        return self.image
