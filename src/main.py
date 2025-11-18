#!/usr/bin/env python3
"""Main application for the e-ink dashboard."""
import time
import signal
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import Config
from src.utils.api_cache import APICache
from src.display.driver import DisplayDriver
from src.display.renderer import Renderer
from src.display.screen_manager import ScreenManager, Screen
from src.touch.handler import TouchHandler, Gesture
from src.widgets.clock import ClockWidget
from src.widgets.weather import WeatherWidget
from src.widgets.portfolio import PortfolioWidget
from src.widgets.network import NetworkWidget


class Dashboard:
    """Main dashboard application."""

    def __init__(self, config_path=None):
        """Initialize the dashboard."""
        print("Initializing e-ink dashboard...")

        # Load configuration
        self.config = Config(config_path)
        print(f"Configuration loaded from {self.config.config_path}")

        # Initialize cache
        self.cache = APICache()

        # Initialize display
        width, height = self.config.get_display_size()
        self.display = DisplayDriver(width, height)
        self.renderer = Renderer(width, height)

        # Initialize touch handler
        self.touch_enabled = self.config.get('touch.enabled', False)
        self.touch_handler = None
        if self.touch_enabled:
            self.touch_handler = TouchHandler(width, height)
            self.touch_handler.set_gesture_callback(self._on_touch_gesture)
            print("Touch input enabled")

        # Determine display mode
        self.multi_screen_mode = self.config.get('display.multi_screen_mode', True)

        if self.multi_screen_mode:
            # Load screens with widgets
            self.screen_manager = self._create_screens()
            print(f"Multi-screen mode: {len(self.screen_manager.screens)} screens")
            self.widgets = None
        else:
            # Legacy single-screen mode
            self.widgets = self._load_widgets()
            print(f"Single-screen mode: {len(self.widgets)} widgets")
            self.screen_manager = None

        # Refresh settings
        self.refresh_interval = self.config.get_refresh_interval()
        print(f"Refresh interval: {self.refresh_interval // 60} minutes")

        self.running = False
        self.last_refresh = None

    def _load_widgets(self):
        """Load enabled widgets from configuration."""
        widgets = []
        enabled = self.config.get_enabled_widgets()

        # Widget registry
        widget_classes = {
            'clock': ClockWidget,
            'weather': WeatherWidget,
            'portfolio': PortfolioWidget,
            'network': NetworkWidget,
        }

        for widget_name in enabled:
            if widget_name in widget_classes:
                widget_class = widget_classes[widget_name]
                widget = widget_class(self.config, self.cache)
                widgets.append(widget)
                print(f"  ✓ Loaded {widget_name} widget")
            else:
                print(f"  ✗ Unknown widget: {widget_name}")

        return widgets

    def _create_screens(self):
        """Create screens for multi-screen mode."""
        screen_manager = ScreenManager()

        # Get screen configurations
        screen_configs = self.config.get('screens', [])

        if not screen_configs:
            # Default: create one screen per widget type
            enabled_widgets = self.config.get_enabled_widgets()
            screen_configs = [{'name': widget, 'widgets': [widget]} for widget in enabled_widgets]

        # Widget registry
        widget_classes = {
            'clock': ClockWidget,
            'weather': WeatherWidget,
            'portfolio': PortfolioWidget,
            'network': NetworkWidget,
        }

        for screen_config in screen_configs:
            screen_name = screen_config.get('name', 'Unnamed')
            widget_names = screen_config.get('widgets', [])

            # Create widgets for this screen
            widgets = []
            for widget_name in widget_names:
                if widget_name in widget_classes:
                    widget_class = widget_classes[widget_name]
                    widget = widget_class(self.config, self.cache)
                    widgets.append(widget)
                else:
                    print(f"  ✗ Unknown widget: {widget_name}")

            if widgets:
                screen = Screen(screen_name, widgets)
                screen_manager.add_screen(screen)
                print(f"  ✓ Created screen '{screen_name}' with {len(widgets)} widgets")

        return screen_manager

    def _on_touch_gesture(self, event):
        """Handle touch gesture events."""
        print(f"Touch gesture: {event.gesture.value}")

        if self.multi_screen_mode and self.screen_manager:
            # Let screen manager handle navigation
            if self.screen_manager.handle_gesture(event):
                # Screen changed, render immediately
                self.render_dashboard(partial=True)

    def update_widgets(self):
        """Update data for all widgets."""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Updating widgets...")

        if self.multi_screen_mode and self.screen_manager:
            # Update current screen only
            self.screen_manager.update_current_screen()
        else:
            # Update all widgets in single-screen mode
            for widget in self.widgets:
                try:
                    widget.update_data()
                except Exception as e:
                    print(f"Error updating {widget.get_name()}: {e}")

    def render_dashboard(self, partial=False):
        """Render dashboard to the display."""
        print("Rendering dashboard...")

        # Create fresh canvas
        self.renderer.create_canvas()

        if self.multi_screen_mode and self.screen_manager:
            # Render current screen
            self.screen_manager.render(self.renderer)
        else:
            # Single-screen mode: render all widgets
            num_widgets = len(self.widgets)
            if num_widgets == 0:
                print("No widgets to render")
                return

            widget_height = self.renderer.height // num_widgets

            # Render each widget
            for i, widget in enumerate(self.widgets):
                y = i * widget_height
                bounds = (0, y, self.renderer.width, widget_height)

                try:
                    widget.render(self.renderer, bounds)

                    # Draw separator line between widgets (except for last one)
                    if i < num_widgets - 1:
                        separator_y = (i + 1) * widget_height - 1
                        self.renderer.draw_horizontal_line(separator_y, thickness=1)

                except Exception as e:
                    print(f"Error rendering {widget.get_name()}: {e}")

        # Display on e-ink screen
        image = self.renderer.get_image()
        self.display.display_image(image, partial=partial)

        print("Dashboard rendered successfully")

    def run_once(self):
        """Run a single update cycle."""
        self.update_widgets()
        # First render is full refresh
        partial = self.last_refresh is not None
        self.render_dashboard(partial=partial)
        self.last_refresh = time.time()

    def run(self):
        """Run the main dashboard loop."""
        print("\n" + "=" * 50)
        print("Starting e-ink dashboard")
        print("=" * 50)

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.running = True

        try:
            # Initialize display with full refresh
            self.display.init(full=True)

            # Initial update
            self.run_once()

            # Main loop
            while self.running:
                # Check for touch input (if enabled)
                if self.touch_handler:
                    touch_event = self.touch_handler.poll()
                    if touch_event:
                        self._on_touch_gesture(touch_event)

                # Calculate time until next refresh
                if self.last_refresh:
                    elapsed = time.time() - self.last_refresh
                    sleep_time = self.refresh_interval - elapsed

                    if sleep_time > 0:
                        print(f"\nNext update in {int(sleep_time // 60)} min {int(sleep_time % 60)} sec")
                        if self.multi_screen_mode:
                            print("Swipe left/right to navigate screens")
                        print("Press Ctrl+C to exit")
                        time.sleep(min(sleep_time, 1))  # Sleep in short chunks for touch responsiveness
                        continue

                # Time for refresh
                self.run_once()

        except KeyboardInterrupt:
            print("\n\nShutdown requested...")
        except Exception as e:
            print(f"\nError in main loop: {e}")
            raise
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown."""
        print("Shutting down dashboard...")
        self.running = False
        self.display.sleep()
        print("Goodbye!")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.running = False


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='E-ink Dashboard')
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file',
        default=None
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (for testing)'
    )

    args = parser.parse_args()

    dashboard = Dashboard(args.config)

    if args.once:
        # Single update for testing
        dashboard.display.init(full=True)
        dashboard.run_once()
        dashboard.shutdown()
    else:
        # Normal operation
        dashboard.run()


if __name__ == '__main__':
    main()
