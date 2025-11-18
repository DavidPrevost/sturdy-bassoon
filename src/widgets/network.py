"""Network monitor widget for tracking network statistics."""
import time
import psutil
from datetime import datetime
from typing import Dict, Optional
from .base import Widget
from src.display.renderer import Renderer


class NetworkWidget(Widget):
    """Displays network statistics and bandwidth usage."""

    def __init__(self, config, cache=None):
        super().__init__(config, cache)
        self.show_bandwidth = config.get('network.show_bandwidth', True)
        self.show_devices = config.get('network.show_devices', False)
        self.interface = config.get('network.interface', None)  # None = auto-detect

        # Network stats
        self.bytes_sent = 0
        self.bytes_recv = 0
        self.speed_up = 0  # KB/s
        self.speed_down = 0  # KB/s
        self.connections = 0
        self.interface_name = "eth0"

        # For calculating speed
        self.last_bytes_sent = 0
        self.last_bytes_recv = 0
        self.last_check_time = None

    def update_data(self) -> bool:
        """Fetch current network statistics."""
        try:
            # Get network I/O counters
            if self.interface:
                # Specific interface
                net_io = psutil.net_io_counters(pernic=True)
                if self.interface in net_io:
                    stats = net_io[self.interface]
                    self.interface_name = self.interface
                else:
                    print(f"Interface {self.interface} not found, using total")
                    stats = psutil.net_io_counters()
                    self.interface_name = "total"
            else:
                # Auto-detect active interface or use total
                stats = psutil.net_io_counters()
                self.interface_name = self._get_active_interface()

            # Calculate speed (bytes per second -> KB/s)
            current_time = time.time()
            if self.last_check_time:
                time_diff = current_time - self.last_check_time
                if time_diff > 0:
                    self.speed_up = (stats.bytes_sent - self.last_bytes_sent) / time_diff / 1024
                    self.speed_down = (stats.bytes_recv - self.last_bytes_recv) / time_diff / 1024

            # Update values
            self.bytes_sent = stats.bytes_sent
            self.bytes_recv = stats.bytes_recv
            self.last_bytes_sent = stats.bytes_sent
            self.last_bytes_recv = stats.bytes_recv
            self.last_check_time = current_time

            # Get connection count if enabled
            if self.show_devices:
                self.connections = len(psutil.net_connections())

            self.last_update = datetime.now()
            print(f"Network updated: ↑{self.speed_up:.1f} KB/s ↓{self.speed_down:.1f} KB/s")
            return True

        except Exception as e:
            print(f"Error fetching network stats: {e}")
            return False

    def _get_active_interface(self) -> str:
        """Get the name of the active network interface."""
        try:
            # Get per-interface stats
            net_io = psutil.net_io_counters(pernic=True)

            # Find interface with most traffic (likely the active one)
            max_bytes = 0
            active_interface = "total"

            for interface, stats in net_io.items():
                total_bytes = stats.bytes_sent + stats.bytes_recv
                if total_bytes > max_bytes and interface not in ['lo', 'lo0']:  # Skip loopback
                    max_bytes = total_bytes
                    active_interface = interface

            return active_interface

        except Exception:
            return "total"

    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human-readable string."""
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 ** 2:
            return f"{bytes_value / 1024:.1f} KB"
        elif bytes_value < 1024 ** 3:
            return f"{bytes_value / (1024 ** 2):.1f} MB"
        else:
            return f"{bytes_value / (1024 ** 3):.2f} GB"

    def _format_speed(self, kbps: float) -> str:
        """Format speed to human-readable string."""
        if kbps < 1:
            return f"{kbps * 1024:.0f} B/s"
        elif kbps < 1024:
            return f"{kbps:.1f} KB/s"
        else:
            return f"{kbps / 1024:.1f} MB/s"

    def render(self, renderer: Renderer, bounds: tuple) -> None:
        """Render network monitor widget."""
        x, y, width, height = bounds

        if self.last_check_time is None:
            self.update_data()

        # Title with interface name
        title = f"Network ({self.interface_name})"
        renderer.draw_text(title, x + 5, y + 3, font_size=11, bold=True)

        # Layout: Two columns or single column based on height
        if height >= 80:
            # Vertical layout (enough space)
            self._render_vertical(renderer, x, y, width, height)
        else:
            # Compact horizontal layout
            self._render_compact(renderer, x, y, width, height)

    def _render_vertical(self, renderer: Renderer, x: int, y: int, width: int, height: int):
        """Render in vertical layout (more space)."""
        start_y = y + 20

        if self.show_bandwidth:
            # Upload speed
            renderer.draw_text("Upload:", x + 5, start_y, font_size=10, bold=True)
            speed_up_text = self._format_speed(self.speed_up)
            renderer.draw_text(
                speed_up_text,
                x + width - 5,
                start_y,
                font_size=10,
                anchor="rt"
            )

            # Download speed
            renderer.draw_text("Download:", x + 5, start_y + 15, font_size=10, bold=True)
            speed_down_text = self._format_speed(self.speed_down)
            renderer.draw_text(
                speed_down_text,
                x + width - 5,
                start_y + 15,
                font_size=10,
                anchor="rt"
            )

            # Total sent
            renderer.draw_text("Sent:", x + 5, start_y + 32, font_size=9)
            sent_text = self._format_bytes(self.bytes_sent)
            renderer.draw_text(
                sent_text,
                x + width - 5,
                start_y + 32,
                font_size=9,
                anchor="rt"
            )

            # Total received
            renderer.draw_text("Received:", x + 5, start_y + 44, font_size=9)
            recv_text = self._format_bytes(self.bytes_recv)
            renderer.draw_text(
                recv_text,
                x + width - 5,
                start_y + 44,
                font_size=9,
                anchor="rt"
            )

        if self.show_devices:
            # Connection count
            renderer.draw_text(
                f"Connections: {self.connections}",
                x + 5,
                start_y + 58,
                font_size=9
            )

    def _render_compact(self, renderer: Renderer, x: int, y: int, width: int, height: int):
        """Render in compact layout (limited space)."""
        start_y = y + 18

        if self.show_bandwidth:
            # Upload (with arrow)
            upload_label = "↑"
            renderer.draw_text(upload_label, x + 5, start_y, font_size=10, bold=True)
            speed_up_text = self._format_speed(self.speed_up)
            renderer.draw_text(speed_up_text, x + 20, start_y, font_size=10)

            # Download (with arrow)
            download_label = "↓"
            mid_x = x + width // 2 + 10
            renderer.draw_text(download_label, mid_x, start_y, font_size=10, bold=True)
            speed_down_text = self._format_speed(self.speed_down)
            renderer.draw_text(speed_down_text, mid_x + 15, start_y, font_size=10)

            # Totals on second line
            sent_text = f"Sent: {self._format_bytes(self.bytes_sent)}"
            renderer.draw_text(sent_text, x + 5, start_y + 15, font_size=8)

            recv_text = f"Recv: {self._format_bytes(self.bytes_recv)}"
            renderer.draw_text(
                recv_text,
                x + width - 5,
                start_y + 15,
                font_size=8,
                anchor="rt"
            )
