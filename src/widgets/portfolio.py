"""Portfolio widget for tracking stocks and cryptocurrency."""
import requests
from datetime import datetime
from typing import List, Dict, Optional
from .base import Widget
from src.display.renderer import Renderer


class PortfolioWidget(Widget):
    """Displays stock and cryptocurrency prices."""

    def __init__(self, config, cache=None):
        super().__init__(config, cache)
        self.symbols = config.get('portfolio.symbols', [])
        self.show_change = config.get('portfolio.show_change', True)
        self.finnhub_api_key = config.get('portfolio.finnhub_api_key', '')
        self.holdings = []  # List of (symbol, price, change_pct, type) tuples
        self.scroll_offset = 0  # For pagination
        self.items_per_page = 4

    def update_data(self) -> bool:
        """Fetch current prices for all symbols."""
        if not self.symbols:
            return False

        if self.cache is None:
            return self._fetch_prices()

        # Cache for 5 minutes (stock data updates frequently)
        cache_key = f"portfolio_{'_'.join(self.symbols)}"
        data = self.cache.get(
            cache_key,
            ttl_seconds=300,  # 5 minutes
            fetch_func=self._fetch_prices
        )

        if data:
            self.last_update = datetime.now()
            return True
        return False

    def _fetch_prices(self) -> dict:
        """Fetch prices for all symbols."""
        self.holdings = []

        for symbol in self.symbols:
            try:
                # Determine if it's crypto or stock
                if self._is_crypto_symbol(symbol):
                    data = self._fetch_crypto_price(symbol)
                else:
                    data = self._fetch_stock_price(symbol)

                if data:
                    self.holdings.append(data)

            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                # Add placeholder for failed symbols
                self.holdings.append((symbol, "--", 0.0, "error"))

        print(f"Portfolio updated: {len(self.holdings)} symbols")
        return {"holdings": self.holdings}

    def _is_crypto_symbol(self, symbol: str) -> bool:
        """Check if symbol looks like a crypto ticker."""
        # Common crypto patterns: BTC-USD, ETH-USD, or just BTC, ETH, etc.
        crypto_keywords = ['BTC', 'ETH', 'USDT', 'BNB', 'SOL', 'ADA', 'DOGE', 'XRP', 'DOT', 'MATIC']
        symbol_base = symbol.split('-')[0].upper()
        return symbol_base in crypto_keywords or '-USD' in symbol.upper()

    def _fetch_crypto_price(self, symbol: str) -> Optional[tuple]:
        """Fetch crypto price from CoinGecko API (free, no key)."""
        try:
            # Parse symbol (e.g., BTC-USD -> bitcoin)
            symbol_base = symbol.split('-')[0].upper()

            # Map common symbols to CoinGecko IDs
            coin_map = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'USDT': 'tether',
                'BNB': 'binancecoin',
                'SOL': 'solana',
                'ADA': 'cardano',
                'DOGE': 'dogecoin',
                'XRP': 'ripple',
                'DOT': 'polkadot',
                'MATIC': 'matic-network',
                'AVAX': 'avalanche-2',
                'LINK': 'chainlink',
                'UNI': 'uniswap',
                'ATOM': 'cosmos',
                'LTC': 'litecoin',
            }

            coin_id = coin_map.get(symbol_base)
            if not coin_id:
                print(f"Unknown crypto symbol: {symbol}")
                return None

            # CoinGecko free API
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': coin_id,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if coin_id in data:
                price = data[coin_id]['usd']
                change_pct = data[coin_id].get('usd_24h_change', 0.0)

                return (symbol, price, change_pct, 'crypto')

        except Exception as e:
            print(f"Error fetching crypto {symbol}: {e}")
            return None

    def _fetch_stock_price(self, symbol: str) -> Optional[tuple]:
        """Fetch stock price using Finnhub API."""
        if not self.finnhub_api_key:
            print(f"No Finnhub API key configured for {symbol}")
            return None

        try:
            url = "https://finnhub.io/api/v1/quote"
            params = {
                'symbol': symbol.upper(),
                'token': self.finnhub_api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Finnhub returns: c (current), d (change), dp (percent change),
            # h (high), l (low), o (open), pc (previous close)
            current_price = data.get('c', 0)
            change_pct = data.get('dp', 0)  # dp is percent change

            # Check if we got valid data (Finnhub returns 0 for invalid symbols)
            if current_price == 0:
                print(f"No data returned for {symbol}")
                return None

            return (symbol, current_price, change_pct, 'stock')

        except Exception as e:
            print(f"Error fetching stock {symbol}: {e}")
            return None

    def scroll_up(self):
        """Scroll up by one page in the holdings list."""
        if self.scroll_offset > 0:
            # Move by full page (items_per_page)
            self.scroll_offset = max(0, self.scroll_offset - self.items_per_page)
            return True
        return False

    def scroll_down(self):
        """Scroll down by one page in the holdings list."""
        max_offset = max(0, len(self.holdings) - self.items_per_page)
        if self.scroll_offset < max_offset:
            # Move by full page (items_per_page)
            self.scroll_offset = min(max_offset, self.scroll_offset + self.items_per_page)
            return True
        return False

    def render(self, renderer: Renderer, bounds: tuple) -> None:
        """Render portfolio widget."""
        x, y, width, height = bounds

        if not self.holdings:
            self.update_data()

        if not self.holdings:
            # No data to display
            renderer.draw_text(
                "No portfolio data",
                x + width // 2,
                y + height // 2,
                font_size=12,
                anchor="mm"
            )
            return

        # Title with page indicator
        total_pages = (len(self.holdings) + self.items_per_page - 1) // self.items_per_page
        current_page = (self.scroll_offset // self.items_per_page) + 1
        if total_pages > 1:
            title_text = f"Portfolio ({current_page}/{total_pages})"
        else:
            title_text = "Portfolio"
        renderer.draw_text(title_text, x + 5, y + 3, font_size=12, bold=True)

        # Calculate layout - larger row height for bigger fonts
        start_y = y + 18
        available_height = height - 22
        line_height = available_height // self.items_per_page

        # Get visible holdings based on scroll offset
        visible_holdings = self.holdings[self.scroll_offset:self.scroll_offset + self.items_per_page]

        # Draw each holding with alternating background
        for i, holding in enumerate(visible_holdings):
            symbol, price, change_pct, asset_type = holding
            line_y = start_y + i * line_height

            # Alternating row background (light gray for even rows)
            if (self.scroll_offset + i) % 2 == 0:
                renderer.draw_rectangle(
                    x + 2, line_y - 2,
                    width - 4, line_height - 1,
                    fill=200  # Light gray
                )

            # Symbol (left column) - larger font
            renderer.draw_text(
                symbol,
                x + 5,
                line_y + 2,
                font_size=13,
                bold=True,
                anchor="lt"
            )

            # Price (center column) - larger font
            if isinstance(price, (int, float)):
                if price < 1:
                    price_text = f"${price:.4f}"
                elif price < 100:
                    price_text = f"${price:.2f}"
                else:
                    price_text = f"${price:,.0f}"
            else:
                price_text = str(price)

            renderer.draw_text(
                price_text,
                x + 75,
                line_y + 2,
                font_size=12,
                anchor="lt"
            )

            # Change percentage (right column) - larger font
            if self.show_change and isinstance(change_pct, (int, float)):
                change_text = f"{change_pct:+.1f}%"

                renderer.draw_text(
                    change_text,
                    x + width - 5,
                    line_y + 2,
                    font_size=12,
                    anchor="rt"
                )

        # Show scroll hints on left side (to avoid overlap with navigation arrows)
        if total_pages > 1:
            # Position arrows on the left edge, vertically centered
            arrow_x = x + 3
            if self.scroll_offset > 0:
                renderer.draw_text("▲", arrow_x, y + height // 3, font_size=8, anchor="lt")
            if self.scroll_offset + self.items_per_page < len(self.holdings):
                renderer.draw_text("▼", arrow_x, y + 2 * height // 3, font_size=8, anchor="lt")
