"""News widget using RSS feeds."""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional, List
from .base import Widget
from src.display.renderer import Renderer


class NewsWidget(Widget):
    """News widget displaying headlines from RSS feeds."""

    # Default RSS feeds
    DEFAULT_FEEDS = [
        ('https://feeds.bbci.co.uk/news/world/rss.xml', 'BBC World'),
        ('https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml', 'NY Times'),
        ('https://feeds.npr.org/1001/rss.xml', 'NPR News'),
    ]

    def __init__(self, config, cache=None):
        super().__init__(config, cache)
        # Handle both old tuple format and new dict format
        feeds_config = config.get('news.feeds', self.DEFAULT_FEEDS)
        if feeds_config and isinstance(feeds_config[0], dict):
            # New format: list of dicts with url and name
            self.feeds = [(f['url'], f['name']) for f in feeds_config]
        else:
            # Old format: list of tuples
            self.feeds = feeds_config
        self.max_headlines = config.get('news.max_headlines', 5)
        self.headlines = []  # List of (title, source) tuples

    def update_data(self) -> bool:
        """Fetch headlines from RSS feeds."""
        if self.cache:
            cache_key = "news_headlines"
            data = self.cache.get(
                cache_key,
                ttl_seconds=600,  # 10 minutes
                fetch_func=self._fetch_headlines
            )
            if data:
                # Restore headlines from cached data
                self.headlines = data.get('headlines', [])
                self.last_update = datetime.now()
                return True
            return False
        return self._fetch_headlines() is not None

    def _fetch_headlines(self) -> Optional[dict]:
        """Fetch headlines from all configured RSS feeds."""
        self.headlines = []

        for feed_url, source_name in self.feeds:
            try:
                response = requests.get(feed_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                response.raise_for_status()

                # Parse RSS XML
                root = ET.fromstring(response.content)

                # Find items (works for both RSS 2.0 and Atom)
                items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')

                for item in items[:3]:  # Get up to 3 from each feed
                    # Try different title tag locations
                    title_elem = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
                    if title_elem is not None and title_elem.text:
                        title = title_elem.text.strip()
                        # Clean up title
                        title = title.replace('\n', ' ').strip()
                        if title:
                            self.headlines.append((title, source_name))

                print(f"✓ Fetched {len(items[:3])} headlines from {source_name}")

            except Exception as e:
                print(f"Error fetching {source_name}: {e}")

        # Limit total headlines
        self.headlines = self.headlines[:self.max_headlines]

        # Only cache if we got some headlines
        if self.headlines:
            return {'headlines': self.headlines}
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

        # Title (closer to top edge)
        renderer.draw_text(
            "News",
            center_x,
            y + 5,
            font_size=9,
            bold=True,
            anchor="mt"
        )

        if self.headlines:
            title, source = self.headlines[0]

            # Truncate title to fit quadrant (roughly 18 chars per line with larger font)
            max_chars = 36
            if len(title) > max_chars:
                title = title[:max_chars-3] + "..."

            # Split into 2 lines if needed
            if len(title) > 18:
                mid = len(title) // 2
                # Find nearest space
                space_idx = title.rfind(' ', 0, mid + 5)
                if space_idx > mid - 5:
                    line1 = title[:space_idx]
                    line2 = title[space_idx+1:]
                else:
                    line1 = title[:18]
                    line2 = title[18:]

                renderer.draw_text(
                    line1,
                    center_x,
                    center_y - 4,
                    font_size=8,
                    anchor="mm"
                )
                renderer.draw_text(
                    line2,
                    center_x,
                    center_y + 8,
                    font_size=8,
                    anchor="mm"
                )
            else:
                renderer.draw_text(
                    title,
                    center_x,
                    center_y + 2,
                    font_size=8,
                    anchor="mm"
                )

            # Source (closer to bottom edge)
            renderer.draw_text(
                source,
                center_x,
                y + height - 5,
                font_size=7,
                bold=True,
                anchor="mb"
            )
        else:
            renderer.draw_text(
                "No news",
                center_x,
                center_y,
                font_size=10,
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
