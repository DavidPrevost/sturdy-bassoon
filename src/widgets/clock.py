"""Clock widget showing current time and date."""
from datetime import datetime
from .base import Widget
from src.display.renderer import Renderer


class ClockWidget(Widget):
    """Displays current time and date."""

    def __init__(self, config, cache=None):
        super().__init__(config, cache)
        self.current_time = None
        self.current_date = None

    def update_data(self) -> bool:
        """Update time and date."""
        now = datetime.now()
        self.current_time = now.strftime("%I:%M %p").lstrip('0')
        self.current_date = now.strftime("%A, %B %d")
        self.last_update = now
        return True

    def render(self, renderer: Renderer, bounds: tuple) -> None:
        """Render clock widget."""
        x, y, width, height = bounds

        if self.current_time is None:
            self.update_data()

        # Adjust font sizes based on available height
        # For half-screen (61px), use smaller fonts to prevent overlap
        if height < 80:
            time_font = 16
            date_font = 9
        else:
            time_font = 20
            date_font = 11

        # Draw time centered in upper portion of bounds
        time_y = y + height // 3
        renderer.draw_text(
            self.current_time,
            x + width // 2,
            time_y,
            font_size=time_font,
            bold=True,
            anchor="mm"
        )

        # Draw date centered in lower portion of bounds
        date_y = y + 2 * height // 3
        renderer.draw_text(
            self.current_date,
            x + width // 2,
            date_y,
            font_size=date_font,
            bold=False,
            anchor="mm"
        )
