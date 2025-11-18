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
from src.widgets.clock import ClockWidget
from src.widgets.weather import WeatherWidget


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

        # Load widgets
        self.widgets = self._load_widgets()
        print(f"Loaded {len(self.widgets)} widgets: {[w.get_name() for w in self.widgets]}")

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

    def update_widgets(self):
        """Update data for all widgets."""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Updating widgets...")
        for widget in self.widgets:
            try:
                widget.update_data()
            except Exception as e:
                print(f"Error updating {widget.get_name()}: {e}")

    def render_dashboard(self, partial=False):
        """Render all widgets to the display."""
        print("Rendering dashboard...")

        # Create fresh canvas
        self.renderer.create_canvas()

        # Calculate widget layout
        # For now: split vertically among widgets
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
                # Calculate time until next refresh
                if self.last_refresh:
                    elapsed = time.time() - self.last_refresh
                    sleep_time = self.refresh_interval - elapsed

                    if sleep_time > 0:
                        print(f"\nNext update in {int(sleep_time // 60)} min {int(sleep_time % 60)} sec")
                        print("Press Ctrl+C to exit")
                        time.sleep(min(sleep_time, 60))  # Sleep in chunks to be responsive
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
