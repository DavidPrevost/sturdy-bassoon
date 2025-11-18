"""Screen manager for multi-screen navigation."""
from typing import List, Dict, Optional
from src.widgets.base import Widget
from src.display.renderer import Renderer
from src.touch.handler import TouchEvent, Gesture


class Screen:
    """Represents a single screen in the dashboard."""

    def __init__(self, name: str, widgets: List[Widget]):
        self.name = name
        self.widgets = widgets
        self.title = name.replace('_', ' ').title()

    def update_data(self) -> bool:
        """Update data for all widgets on this screen."""
        updated = False
        for widget in self.widgets:
            try:
                if widget.update_data():
                    updated = True
            except Exception as e:
                print(f"Error updating {widget.get_name()} on {self.name}: {e}")
        return updated

    def render(self, renderer: Renderer) -> None:
        """Render all widgets on this screen."""
        if not self.widgets:
            return

        # Split screen among widgets
        num_widgets = len(self.widgets)
        widget_height = renderer.height // num_widgets

        for i, widget in enumerate(self.widgets):
            y = i * widget_height
            bounds = (0, y, renderer.width, widget_height)

            try:
                widget.render(renderer, bounds)

                # Draw separator line between widgets (except for last one)
                if i < num_widgets - 1:
                    separator_y = (i + 1) * widget_height - 1
                    renderer.draw_horizontal_line(separator_y, thickness=1)

            except Exception as e:
                print(f"Error rendering {widget.get_name()} on {self.name}: {e}")


class ScreenManager:
    """Manages multiple screens and navigation between them."""

    def __init__(self):
        self.screens: List[Screen] = []
        self.current_index = 0
        self.show_indicators = True

    def add_screen(self, screen: Screen):
        """Add a screen to the manager."""
        self.screens.append(screen)

    def get_current_screen(self) -> Optional[Screen]:
        """Get the currently active screen."""
        if 0 <= self.current_index < len(self.screens):
            return self.screens[self.current_index]
        return None

    def next_screen(self):
        """Navigate to the next screen (wraps around)."""
        if self.screens:
            self.current_index = (self.current_index + 1) % len(self.screens)
            print(f"Switched to screen: {self.screens[self.current_index].name}")

    def previous_screen(self):
        """Navigate to the previous screen (wraps around)."""
        if self.screens:
            self.current_index = (self.current_index - 1) % len(self.screens)
            print(f"Switched to screen: {self.screens[self.current_index].name}")

    def go_to_screen(self, index: int):
        """Go to a specific screen by index."""
        if 0 <= index < len(self.screens):
            self.current_index = index
            print(f"Switched to screen: {self.screens[self.current_index].name}")

    def handle_gesture(self, event: TouchEvent) -> bool:
        """
        Handle touch gesture for navigation.

        Args:
            event: TouchEvent from touch handler

        Returns:
            True if gesture caused a screen change
        """
        if event.gesture == Gesture.SWIPE_LEFT:
            self.next_screen()
            return True
        elif event.gesture == Gesture.SWIPE_RIGHT:
            self.previous_screen()
            return True
        elif event.gesture == Gesture.TAP and event.position:
            # Tap on left/right edges to navigate
            x, y = event.position
            width = 250  # Display width
            edge_zone = width // 5  # 20% on each side

            if x < edge_zone:
                self.previous_screen()
                return True
            elif x > width - edge_zone:
                self.next_screen()
                return True

        return False

    def render(self, renderer: Renderer):
        """Render the current screen."""
        current_screen = self.get_current_screen()
        if not current_screen:
            return

        # Render the screen
        current_screen.render(renderer)

        # Draw screen indicators at the bottom
        if self.show_indicators and len(self.screens) > 1:
            self._draw_screen_indicators(renderer)

    def _draw_screen_indicators(self, renderer: Renderer):
        """Draw dots at the bottom indicating current screen."""
        num_screens = len(self.screens)
        dot_size = 3
        dot_spacing = 8
        total_width = (num_screens * dot_size) + ((num_screens - 1) * (dot_spacing - dot_size))

        # Position at bottom center
        start_x = (renderer.width - total_width) // 2
        y = renderer.height - 6

        for i in range(num_screens):
            x = start_x + i * dot_spacing
            # Filled circle for current screen, outline for others
            if i == self.current_index:
                renderer.draw_rectangle(x, y, dot_size, dot_size, fill=0)
            else:
                renderer.draw_rectangle(x, y, dot_size, dot_size, outline=0)

    def update_current_screen(self):
        """Update data for the current screen."""
        current_screen = self.get_current_screen()
        if current_screen:
            current_screen.update_data()


class SingleScreenView:
    """
    A view that shows one widget per screen.

    Useful for portfolio, network stats, etc. where you want
    each widget to take the full screen.
    """

    def __init__(self, widgets: List[Widget]):
        self.widgets = widgets
        self.current_index = 0

    def next_widget(self):
        """Show next widget."""
        if self.widgets:
            self.current_index = (self.current_index + 1) % len(self.widgets)

    def previous_widget(self):
        """Show previous widget."""
        if self.widgets:
            self.current_index = (self.current_index - 1) % len(self.widgets)

    def render(self, renderer: Renderer):
        """Render current widget full screen."""
        if 0 <= self.current_index < len(self.widgets):
            widget = self.widgets[self.current_index]
            bounds = (0, 0, renderer.width, renderer.height)
            widget.render(renderer, bounds)
