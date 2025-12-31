"""News widget using RSS feeds."""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional, List, Tuple
from .base import Widget
from src.display.renderer import Renderer


class NewsWidget(Widget):
    """News widget displaying headlines from RSS feeds."""

    # Default RSS feed - BBC World News
    DEFAULT_FEED_URL = 'https://feeds.bbci.co.uk/news/world/rss.xml'
    DEFAULT_FEED_NAME = 'BBC World'
    MAX_CACHED_HEADLINES = 12  # Max headlines to keep (3 pages of 4)

    def __init__(self, config, cache=None):
        super().__init__(config, cache)
        self.feed_url = config.get('news.feed_url', self.DEFAULT_FEED_URL)
        self.feed_name = config.get('news.feed_name', self.DEFAULT_FEED_NAME)
        self.max_headlines = config.get('news.max_headlines', 5)
        # Headlines now store (title, description, source)
        self.headlines: List[Tuple[str, str, str]] = []
        self.rotation_index = 0  # Current headline to display in widget
        self._headline_cache: List[Tuple[str, str, str]] = []  # Cache for older headlines

        # Pagination for detail view
        self.current_page = 0
        self.headlines_per_page = 4

        # Article detail view state (-1 = not showing detail)
        self.selected_article_index = -1
        self.article_scroll_offset = 0  # For scrolling long descriptions

    def rotate(self) -> None:
        """Rotate to the next headline. Called on each clock update."""
        if self.headlines:
            self.rotation_index = (self.rotation_index + 1) % len(self.headlines)
            print(f"[News] Rotated to headline {self.rotation_index + 1}/{len(self.headlines)}")

    def get_current_headline(self) -> Optional[Tuple[str, str, str]]:
        """Get the current headline (title, description, source) based on rotation index."""
        if not self.headlines:
            return None
        idx = self.rotation_index % len(self.headlines)
        return self.headlines[idx]

    def get_headlines_page(self, page: int, per_page: int = 4) -> List[Tuple[str, str, str]]:
        """Get a page of headlines starting from rotation index."""
        if not self.headlines:
            return []

        start_idx = self.rotation_index % len(self.headlines)
        result = []
        for i in range(per_page):
            offset = page * per_page + i
            if offset < len(self.headlines):
                idx = (start_idx + offset) % len(self.headlines)
                result.append(self.headlines[idx])
        return result

    def get_headline_by_index(self, display_index: int) -> Optional[Tuple[str, str, str]]:
        """Get a headline by its display index (relative to rotation)."""
        if not self.headlines or display_index >= len(self.headlines):
            return None
        start_idx = self.rotation_index % len(self.headlines)
        actual_idx = (start_idx + display_index) % len(self.headlines)
        return self.headlines[actual_idx]

    def get_total_pages(self, per_page: int = 4) -> int:
        """Get total number of pages."""
        if not self.headlines:
            return 0
        return (len(self.headlines) + per_page - 1) // per_page

    # Navigation methods for detail view
    def next_page(self) -> bool:
        """Go to next page of headlines. Returns True if page changed."""
        max_page = self.get_total_pages(self.headlines_per_page) - 1
        if self.current_page < max_page:
            self.current_page += 1
            print(f"[News] Page {self.current_page + 1}/{max_page + 1}")
            return True
        return False

    def prev_page(self) -> bool:
        """Go to previous page of headlines. Returns True if page changed."""
        if self.current_page > 0:
            self.current_page -= 1
            max_page = self.get_total_pages(self.headlines_per_page)
            print(f"[News] Page {self.current_page + 1}/{max_page}")
            return True
        return False

    def select_article(self, tap_index: int) -> bool:
        """
        Select an article to show its summary.

        Args:
            tap_index: Index within current page (0-3)

        Returns:
            True if article was selected
        """
        # Calculate actual headline index
        actual_index = self.current_page * self.headlines_per_page + tap_index
        if actual_index < len(self.headlines):
            self.selected_article_index = actual_index
            self.article_scroll_offset = 0
            title = self.headlines[actual_index][0][:40]
            print(f"[News] Selected article: {title}...")
            return True
        return False

    def close_article(self) -> bool:
        """Close article detail view. Returns True if was showing article."""
        if self.selected_article_index >= 0:
            self.selected_article_index = -1
            self.article_scroll_offset = 0
            print("[News] Closed article detail")
            return True
        return False

    def is_showing_article(self) -> bool:
        """Check if currently showing article detail."""
        return self.selected_article_index >= 0

    def scroll_article_down(self) -> bool:
        """Scroll article description down. Returns True if scrolled."""
        # We'll implement actual scrolling based on content length during render
        self.article_scroll_offset += 1
        return True

    def scroll_article_up(self) -> bool:
        """Scroll article description up. Returns True if scrolled."""
        if self.article_scroll_offset > 0:
            self.article_scroll_offset -= 1
            return True
        return False

    def get_tap_zone(self, position: Tuple[int, int], height: int = 122) -> Optional[int]:
        """
        Get which headline was tapped based on position.

        Args:
            position: (x, y) tap coordinates
            height: Screen height

        Returns:
            Headline index within current page (0-3), or None
        """
        if position is None:
            return None

        x, y = position

        # Skip title area (top ~16px)
        content_start = 16
        content_height = height - content_start

        if y < content_start:
            return None

        # Each headline takes 1/4 of remaining height
        headline_height = content_height // 4
        tap_index = (y - content_start) // headline_height

        if 0 <= tap_index < 4:
            return tap_index
        return None

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

            for item in items[:self.MAX_CACHED_HEADLINES]:
                title_elem = item.find('title')
                if title_elem is None:
                    title_elem = item.find('{http://www.w3.org/2005/Atom}title')

                # Get description/summary
                desc_elem = item.find('description')
                if desc_elem is None:
                    desc_elem = item.find('{http://www.w3.org/2005/Atom}summary')

                if title_elem is not None and title_elem.text:
                    title = title_elem.text.strip().replace('\n', ' ')
                    description = ""
                    if desc_elem is not None and desc_elem.text:
                        # Clean up description - remove HTML tags if present
                        desc_text = desc_elem.text.strip()
                        # Simple HTML tag removal
                        import re
                        description = re.sub(r'<[^>]+>', '', desc_text).strip()
                        description = description.replace('\n', ' ').replace('  ', ' ')

                    if title:
                        self.headlines.append((title, description, self.feed_name))
                        print(f"[News] Added headline: {title[:50]}...")

            print(f"✓ News: Got {len(self.headlines)} headlines from {self.feed_name}")

            # If we got fewer than MAX, fill from cache with non-duplicate headlines
            if len(self.headlines) < self.MAX_CACHED_HEADLINES and self._headline_cache:
                existing_titles = {h[0] for h in self.headlines}
                for cached in self._headline_cache:
                    if cached[0] not in existing_titles and len(self.headlines) < self.MAX_CACHED_HEADLINES:
                        self.headlines.append(cached)
                        existing_titles.add(cached[0])
                print(f"[News] Filled to {len(self.headlines)} headlines from cache")

            # Update cache with current headlines
            self._headline_cache = self.headlines.copy()

            # Reset rotation if it's beyond new headline count
            if self.rotation_index >= len(self.headlines):
                self.rotation_index = 0

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
            # Get headline at current rotation index
            idx = self.rotation_index % len(self.headlines)
            title, description, source = self.headlines[idx]

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
        """Render headlines list or article detail for full screen view."""
        x, y, width, height = bounds

        # Check if showing article detail
        if self.is_showing_article():
            self._render_article_detail(renderer, bounds)
            return

        # Render headline list with pagination
        self._render_headline_list(renderer, bounds)

    def _render_headline_list(self, renderer: Renderer, bounds: tuple) -> None:
        """Render paginated list of headlines."""
        x, y, width, height = bounds

        # Title with page indicator
        total_pages = self.get_total_pages(self.headlines_per_page)
        if total_pages > 1:
            title_text = f"News ({self.current_page + 1}/{total_pages})"
        else:
            title_text = "News"

        renderer.draw_text(
            title_text,
            x + 5,
            y + 2,
            font_size=10,
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

        # Draw 4 headlines for current page
        start_y = y + 16
        block_height = (height - 16) // 4  # ~26px per headline block

        # Get headlines for current page
        start_idx = self.current_page * self.headlines_per_page
        page_headlines = self.headlines[start_idx:start_idx + self.headlines_per_page]

        for i, (title, description, source) in enumerate(page_headlines):
            block_y = start_y + i * block_height

            # Word wrap title into 2 lines
            # ~30 chars per line at font_size 10
            chars_per_line = 32

            if len(title) <= chars_per_line:
                # Single line - center it vertically in block
                renderer.draw_text(
                    f"• {title}",
                    x + 3,
                    block_y + block_height // 2 - 5,
                    font_size=10,
                    anchor="lt"
                )
            else:
                # Split into 2 lines at word boundary
                split_point = title.rfind(' ', 0, chars_per_line)
                if split_point < chars_per_line // 2:
                    split_point = chars_per_line  # Force split if no good word boundary

                line1 = title[:split_point].strip()
                line2 = title[split_point:].strip()

                # Truncate line2 if still too long
                if len(line2) > chars_per_line - 2:
                    line2 = line2[:chars_per_line - 5] + "..."

                # Draw both lines
                renderer.draw_text(
                    f"• {line1}",
                    x + 3,
                    block_y,
                    font_size=10,
                    anchor="lt"
                )
                renderer.draw_text(
                    f"  {line2}",
                    x + 3,
                    block_y + 12,
                    font_size=10,
                    anchor="lt"
                )

        # Draw page navigation hints at bottom
        if total_pages > 1:
            if self.current_page > 0:
                renderer.draw_text("↑", x + width // 2 - 15, y + height - 8, font_size=8, anchor="mm")
            if self.current_page < total_pages - 1:
                renderer.draw_text("↓", x + width // 2 + 15, y + height - 8, font_size=8, anchor="mm")

    def _render_article_detail(self, renderer: Renderer, bounds: tuple) -> None:
        """Render article summary view."""
        x, y, width, height = bounds

        if self.selected_article_index < 0 or self.selected_article_index >= len(self.headlines):
            return

        title, description, source = self.headlines[self.selected_article_index]

        # Header with source and back hint
        renderer.draw_text(
            f"← {source}",
            x + 3,
            y + 2,
            font_size=8,
            bold=True
        )

        # Title area (top portion)
        title_y = y + 14
        chars_per_line = 30  # Same as headline font

        # Word wrap title
        title_lines = self._wrap_text(title, chars_per_line)
        for i, line in enumerate(title_lines[:2]):  # Max 2 lines for title
            renderer.draw_text(
                line,
                x + 3,
                title_y + i * 12,
                font_size=10,
                bold=True,
                anchor="lt"
            )

        # Separator line
        sep_y = title_y + len(title_lines[:2]) * 12 + 4
        renderer.draw_horizontal_line(sep_y, thickness=1)

        # Description area
        desc_start_y = sep_y + 6
        desc_height = height - (desc_start_y - y) - 8  # Leave room at bottom
        lines_visible = desc_height // 12  # ~12px per line at font_size 10

        if description:
            # Wrap description text
            desc_lines = self._wrap_text(description, chars_per_line)

            # Apply scroll offset
            start_line = self.article_scroll_offset
            visible_lines = desc_lines[start_line:start_line + lines_visible]

            for i, line in enumerate(visible_lines):
                renderer.draw_text(
                    line,
                    x + 3,
                    desc_start_y + i * 12,
                    font_size=10,
                    anchor="lt"
                )

            # Scroll indicators
            if start_line > 0:
                renderer.draw_text("↑", x + width - 10, desc_start_y, font_size=8, anchor="rt")
            if start_line + lines_visible < len(desc_lines):
                renderer.draw_text("↓", x + width - 10, y + height - 10, font_size=8, anchor="rb")
        else:
            renderer.draw_text(
                "No summary available",
                x + width // 2,
                desc_start_y + 20,
                font_size=10,
                anchor="mm"
            )

        # Back hint at bottom
        renderer.draw_text(
            "← swipe to go back",
            x + width // 2,
            y + height - 3,
            font_size=7,
            anchor="mb"
        )

    def _wrap_text(self, text: str, max_chars: int) -> List[str]:
        """Wrap text into lines of max_chars length."""
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if not current_line:
                current_line = word
            elif len(current_line) + 1 + len(word) <= max_chars:
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines
