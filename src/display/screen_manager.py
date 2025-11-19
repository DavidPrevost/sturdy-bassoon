"""Screen manager for multi-screen navigation."""
from typing import List, Dict, Optional, Tuple
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

    def get_tap_zone(self, position: Tuple[int, int]) -> Optional[int]:
        """Get which widget zone was tapped. Returns widget index or None."""
        return None  # Standard screens don't have tap zones


class QuadrantScreen(Screen):
    """
    A screen with 4 quadrants in a 2x2 grid layout.

    Layout:
    +------------+------------+
    | Upper Left | Upper Right|
    | (widget 0) | (widget 1) |
    +------------+------------+
    | Lower Left | Lower Right|
    | (widget 2) | (widget 3) |
    +------------+------------+
    """

    def __init__(self, name: str, widgets: List[Widget], detail_screens: List[str] = None):
        """
        Initialize quadrant screen.

        Args:
            name: Screen name
            widgets: List of exactly 4 widgets for each quadrant
            detail_screens: List of screen names to navigate to when each quadrant is tapped
        """
        super().__init__(name, widgets)
        self.detail_screens = detail_screens or [None, None, None, None]

        if len(widgets) != 4:
            print(f"Warning: QuadrantScreen expects 4 widgets, got {len(widgets)}")

    def render(self, renderer: Renderer) -> None:
        """Render widgets in 2x2 quadrant layout."""
        if not self.widgets:
            return

        # Calculate quadrant dimensions
        half_width = renderer.width // 2
        half_height = renderer.height // 2

        # Quadrant positions: (x, y, width, height)
        quadrants = [
            (0, 0, half_width, half_height),              # Upper left
            (half_width, 0, half_width, half_height),     # Upper right
            (0, half_height, half_width, half_height),    # Lower left
            (half_width, half_height, half_width, half_height),  # Lower right
        ]

        # Render each widget in its quadrant
        for i, widget in enumerate(self.widgets[:4]):
            if widget is None:
                continue

            x, y, w, h = quadrants[i]
            bounds = (x, y, w, h)

            try:
                widget.render(renderer, bounds)
            except Exception as e:
                print(f"Error rendering quadrant {i} on {self.name}: {e}")

        # Draw dividing lines
        # Vertical center line
        renderer.draw_vertical_line(half_width, thickness=1)
        # Horizontal center line
        renderer.draw_horizontal_line(half_height, thickness=1)

    def get_tap_zone(self, position: Tuple[int, int]) -> Optional[int]:
        """
        Get which quadrant was tapped.

        Args:
            position: (x, y) tap coordinates

        Returns:
            Quadrant index (0-3) or None
        """
        if position is None:
            return None

        x, y = position
        half_width = 125  # 250 / 2
        half_height = 61  # 122 / 2

        if x < half_width:
            if y < half_height:
                return 0  # Upper left
            else:
                return 2  # Lower left
        else:
            if y < half_height:
                return 1  # Upper right
            else:
                return 3  # Lower right

    def get_detail_screen(self, quadrant: int) -> Optional[str]:
        """Get the detail screen name for a quadrant."""
        if 0 <= quadrant < len(self.detail_screens):
            return self.detail_screens[quadrant]
        return None


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
        """Draw navigation arrows and dots at the bottom."""
        num_screens = len(self.screens)

        # Draw navigation arrows on left and right
        bottom_y = renderer.height - 8

        # Left arrow (previous screen) - only show if not on first screen
        if self.current_index > 0:
            renderer.draw_text(
                "<",
                5,
                bottom_y,
                font_size=10,
                bold=True,
                anchor="lt"
            )

        # Right arrow (next screen) - only show if not on last screen
        if self.current_index < num_screens - 1:
            renderer.draw_text(
                ">",
                renderer.width - 10,
                bottom_y,
                font_size=10,
                bold=True,
                anchor="rt"
            )

        # Draw screen indicator dots in the center
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
