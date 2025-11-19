"""Portfolio summary widget for quadrant display."""
import requests
from datetime import datetime
from typing import Optional, List
from .base import Widget
from src.display.renderer import Renderer


class PortfolioSummaryWidget(Widget):
    """Compact portfolio summary showing total value and daily change."""

    def __init__(self, config, cache=None):
        super().__init__(config, cache)
        self.finnhub_api_key = config.get('portfolio.finnhub_api_key', '')
        self.holdings = config.get('portfolio.holdings', [])

        # Calculated values
        self.total_value = 0.0
        self.total_cost = 0.0
        self.daily_change = 0.0
        self.daily_change_pct = 0.0

    def update_data(self) -> bool:
        """Fetch prices and calculate portfolio summary."""
        if not self.holdings:
            return False

        if self.cache:
            cache_key = "portfolio_summary"
            data = self.cache.get(
                cache_key,
                ttl_seconds=300,
                fetch_func=self._calculate_portfolio
            )
            if data:
                self.last_update = datetime.now()
                return True
            return False
        return self._calculate_portfolio() is not None

    def _calculate_portfolio(self) -> Optional[dict]:
        """Calculate total portfolio value and daily change."""
        self.total_value = 0.0
        self.total_cost = 0.0
        self.daily_change = 0.0
        prev_total = 0.0

        for holding in self.holdings:
            symbol = holding.get('symbol', '')
            shares = holding.get('shares', 0)
            cost_basis = holding.get('cost_basis', 0)

            if not symbol or shares <= 0:
                continue

            # Fetch current price
            price_data = self._fetch_price(symbol)
            if price_data:
                current_price, change_pct = price_data

                # Calculate values
                current_value = shares * current_price
                self.total_value += current_value
                self.total_cost += shares * cost_basis

                # Calculate previous value (before today's change)
                prev_price = current_price / (1 + change_pct / 100) if change_pct != 0 else current_price
                prev_total += shares * prev_price

        # Calculate daily change
        if prev_total > 0:
            self.daily_change = self.total_value - prev_total
            self.daily_change_pct = (self.daily_change / prev_total) * 100

        return {
            'total_value': self.total_value,
            'daily_change': self.daily_change,
            'daily_change_pct': self.daily_change_pct
        }

    def _fetch_price(self, symbol: str) -> Optional[tuple]:
        """Fetch current price and change percent."""
        # Check if crypto
        if self._is_crypto(symbol):
            return self._fetch_crypto_price(symbol)
        else:
            return self._fetch_stock_price(symbol)

    def _is_crypto(self, symbol: str) -> bool:
        """Check if symbol is a cryptocurrency."""
        crypto_keywords = ['BTC', 'ETH', 'USDT', 'BNB', 'SOL', 'ADA', 'DOGE', 'XRP']
        symbol_base = symbol.split('-')[0].upper()
        return symbol_base in crypto_keywords or '-USD' in symbol.upper()

    def _fetch_stock_price(self, symbol: str) -> Optional[tuple]:
        """Fetch stock price from Finnhub."""
        if not self.finnhub_api_key:
            return None

        try:
            url = "https://finnhub.io/api/v1/quote"
            params = {'symbol': symbol.upper(), 'token': self.finnhub_api_key}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            price = data.get('c', 0)
            change_pct = data.get('dp', 0)

            if price == 0:
                return None

            return (price, change_pct)

        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None

    def _fetch_crypto_price(self, symbol: str) -> Optional[tuple]:
        """Fetch crypto price from CoinGecko."""
        try:
            symbol_base = symbol.split('-')[0].upper()
            coin_map = {
                'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
                'ADA': 'cardano', 'DOGE': 'dogecoin', 'XRP': 'ripple'
            }

            coin_id = coin_map.get(symbol_base)
            if not coin_id:
                return None

            url = "https://api.coingecko.com/api/v3/simple/price"
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
                change_pct = data[coin_id].get('usd_24h_change', 0)
                return (price, change_pct)

        except Exception as e:
            print(f"Error fetching crypto {symbol}: {e}")

        return None

    def render(self, renderer: Renderer, bounds: tuple) -> None:
        """Render portfolio summary in quadrant bounds."""
        x, y, width, height = bounds

        if self.total_value == 0:
            self.update_data()

        center_x = x + width // 2
        center_y = y + height // 2

        # Title
        renderer.draw_text(
            "Portfolio",
            center_x,
            y + 8,
            font_size=8,
            bold=True,
            anchor="mt"
        )

        # Total value
        if self.total_value >= 1000:
            value_str = f"${self.total_value:,.0f}"
        else:
            value_str = f"${self.total_value:.2f}"

        renderer.draw_text(
            value_str,
            center_x,
            center_y - 2,
            font_size=12,
            bold=True,
            anchor="mm"
        )

        # Daily change
        if self.daily_change >= 0:
            change_str = f"+${self.daily_change:.2f} ({self.daily_change_pct:+.1f}%)"
        else:
            change_str = f"-${abs(self.daily_change):.2f} ({self.daily_change_pct:+.1f}%)"

        renderer.draw_text(
            change_str,
            center_x,
            center_y + 14,
            font_size=7,
            anchor="mm"
        )
