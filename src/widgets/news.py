"""News widget using RSS feeds."""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional, List
from .base import Widget
from src.display.renderer import Renderer


class NewsWidget(Widget):
    """News widget displaying headlines from RSS feeds."""

    # Simple, reliable RSS feed for testing
    DEFAULT_FEED_URL = 'https://news.ycombinator.com/rss'
    DEFAULT_FEED_NAME = 'Hacker News'

    def __init__(self, config, cache=None):
        super().__init__(config, cache)
        self.feed_url = config.get('news.feed_url', self.DEFAULT_FEED_URL)
        self.feed_name = config.get('news.feed_name', self.DEFAULT_FEED_NAME)
        self.max_headlines = config.get('news.max_headlines', 5)
        self.headlines = []  # List of (title, source) tuples

    def update_data(self) -> bool:
        """Fetch headlines from RSS feed."""
        print(f"[News] Fetching from {self.feed_url}...")

        # Skip cache for now to debug
        result = self._fetch_headlines()
        if result:
            self.last_update = datetime.now()
            return True
        return False

    def _fetch_headlines(self) -> Optional[dict]:
        """Fetch headlines from RSS feed."""
        self.headlines = []

        try:
            print(f"[News] Making request to {self.feed_url}")
            response = requests.get(
                self.feed_url,
                timeout=15,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; EinkDashboard/1.0)',
                    'Accept': 'application/rss+xml, application/xml, text/xml'
                }
            )
            print(f"[News] Response status: {response.status_code}")
            response.raise_for_status()

            # Debug: show first 500 chars of response
            content = response.content
            print(f"[News] Response length: {len(content)} bytes")
            print(f"[News] First 200 chars: {content[:200]}")

            # Parse RSS XML
            root = ET.fromstring(content)
            print(f"[News] XML root tag: {root.tag}")

            # Find items - try multiple methods
            items = root.findall('.//item')
            print(f"[News] Found {len(items)} items with .//item")

            if not items:
                items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
                print(f"[News] Found {len(items)} items with Atom entry")

            if not items:
                # Debug: list all tags
                all_tags = set()
                for elem in root.iter():
                    all_tags.add(elem.tag)
                print(f"[News] All tags in XML: {all_tags}")

            for item in items[:self.max_headlines]:
                title_elem = item.find('title')
                if title_elem is None:
                    title_elem = item.find('{http://www.w3.org/2005/Atom}title')

                if title_elem is not None and title_elem.text:
                    title = title_elem.text.strip().replace('\n', ' ')
                    if title:
                        self.headlines.append((title, self.feed_name))
                        print(f"[News] Added headline: {title[:50]}...")

            print(f"✓ News: Got {len(self.headlines)} headlines from {self.feed_name}")

            if self.headlines:
                return {'headlines': self.headlines}
            return None

        except requests.exceptions.Timeout:
            print(f"✗ News: Request timed out for {self.feed_url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"✗ News: Request failed: {e}")
            return None
        except ET.ParseError as e:
            print(f"✗ News: XML parse error: {e}")
            return None
        except Exception as e:
            print(f"✗ News: Unexpected error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def render(self, renderer: Renderer, bounds: tuple) -> None:
        """Render news headlines."""
        x, y, width, height = bounds

        if not self.headlines:
            self.update_data()

        # Check if this is compact (quadrant) or full screen
        is_compact = height < 80

        if is_compact:
            self._render_compact(renderer, bounds)
        else:
            self._render_full(renderer, bounds)

    def _render_compact(self, renderer: Renderer, bounds: tuple) -> None:
        """Render single headline for quadrant view."""
        x, y, width, height = bounds
        center_x = x + width // 2
        center_y = y + height // 2

        # Title
        renderer.draw_text(
            "News",
            center_x,
            y + 8,
            font_size=8,
            bold=True,
            anchor="mt"
        )

        if self.headlines:
            title, source = self.headlines[0]

            # Truncate title to fit quadrant (roughly 20 chars per line)
            max_chars = 40
            if len(title) > max_chars:
                title = title[:max_chars-3] + "..."

            # Split into 2 lines if needed
            if len(title) > 20:
                mid = len(title) // 2
                # Find nearest space
                space_idx = title.rfind(' ', 0, mid + 5)
                if space_idx > mid - 5:
                    line1 = title[:space_idx]
                    line2 = title[space_idx+1:]
                else:
                    line1 = title[:20]
                    line2 = title[20:]

                renderer.draw_text(
                    line1,
                    center_x,
                    center_y - 4,
                    font_size=7,
                    anchor="mm"
                )
                renderer.draw_text(
                    line2,
                    center_x,
                    center_y + 8,
                    font_size=7,
                    anchor="mm"
                )
            else:
                renderer.draw_text(
                    title,
                    center_x,
                    center_y + 2,
                    font_size=7,
                    anchor="mm"
                )

            # Source
            renderer.draw_text(
                source,
                center_x,
                y + height - 8,
                font_size=6,
                anchor="mb"
            )
        else:
            renderer.draw_text(
                "No news",
                center_x,
                center_y,
                font_size=8,
                anchor="mm"
            )

    def _render_full(self, renderer: Renderer, bounds: tuple) -> None:
        """Render multiple headlines for full screen view."""
        x, y, width, height = bounds

        # Title
        renderer.draw_text(
            "News Headlines",
            x + 5,
            y + 3,
            font_size=11,
            bold=True
        )

        if not self.headlines:
            renderer.draw_text(
                "No headlines available",
                x + width // 2,
                y + height // 2,
                font_size=10,
                anchor="mm"
            )
            return

        # Draw headlines
        start_y = y + 20
        line_height = 18

        for i, (title, source) in enumerate(self.headlines[:5]):
            line_y = start_y + i * line_height

            # Truncate title
            max_chars = 35
            if len(title) > max_chars:
                title = title[:max_chars-3] + "..."

            # Draw bullet and title
            renderer.draw_text(
                f"• {title}",
                x + 5,
                line_y,
                font_size=8,
                anchor="lt"
            )
