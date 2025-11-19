"""Compact clock widget for quadrant display."""
from datetime import datetime
from .base import Widget
from src.display.renderer import Renderer


class ClockCompactWidget(Widget):
    """Compact clock widget showing time and date for quadrant layout."""

    def __init__(self, config, cache=None):
        super().__init__(config, cache)
        self.show_seconds = config.get('clock.show_seconds', False)
        self.time_format = config.get('clock.format', '12h')

    def update_data(self) -> bool:
        """Clock always has current data."""
        self.last_update = datetime.now()
        return True

    def render(self, renderer: Renderer, bounds: tuple) -> None:
        """Render compact clock in quadrant bounds."""
        x, y, width, height = bounds

        now = datetime.now()

        # Format time
        if self.time_format == '24h':
            time_str = now.strftime('%H:%M')
        else:
            time_str = now.strftime('%I:%M %p').lstrip('0')

        # Format date
        date_str = now.strftime('%a, %b %d')

        # Center in quadrant
        center_x = x + width // 2
        center_y = y + height // 2

        # Draw time (larger)
        renderer.draw_text(
            time_str,
            center_x,
            center_y - 8,
            font_size=14,
            bold=True,
            anchor="mm"
        )

        # Draw date (smaller, below time)
        renderer.draw_text(
            date_str,
            center_x,
            center_y + 12,
            font_size=9,
            anchor="mm"
        )
