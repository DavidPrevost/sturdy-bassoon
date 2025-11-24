"""Compact weather widget for quadrant display."""
import requests
from datetime import datetime
from typing import Optional
from .base import Widget
from src.display.renderer import Renderer
from src.utils.geocoding import Geocoder


class WeatherCompactWidget(Widget):
    """Compact weather widget showing current conditions for quadrant layout."""

    def __init__(self, config, cache=None):
        super().__init__(config, cache)
        # Use same location logic as main weather widget
        self.zip_code = config.get('weather.zip_code', None)
        self.latitude = config.get('weather.latitude', 40.7128)
        self.longitude = config.get('weather.longitude', -74.0060)
        self.location_name = config.get('weather.location_name', None)
        self.units = config.get('weather.units', 'fahrenheit')

        # If ZIP code is provided, geocode it (same as main weather widget)
        if self.zip_code and not self.location_name and Geocoder.validate_zip(self.zip_code):
            result = Geocoder.zip_to_coords(self.zip_code)
            if result:
                self.latitude, self.longitude, self.location_name = result

        # Weather data
        self.temperature = None
        self.condition = None
        self.high = None
        self.low = None
        self.weather_code = None

    def _get_weather_icon(self, code: int) -> str:
        """Get a simple icon character for weather code."""
        # Map weather codes to simple ASCII/Unicode icons
        if code == 0:
            return "☀"  # Clear
        elif code in [1, 2]:
            return "⛅"  # Partly cloudy
        elif code == 3:
            return "☁"  # Overcast
        elif code in [45, 48]:
            return "🌫"  # Fog
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
            return "🌧"  # Rain/drizzle
        elif code in [71, 73, 75, 77, 85, 86]:
            return "❄"  # Snow
        elif code in [95, 96, 99]:
            return "⚡"  # Thunderstorm
        else:
            return "?"

    def update_data(self) -> bool:
        """Fetch current weather data."""
        if self.cache:
            # Use same cache key as main weather widget to share data
            cache_key = f"weather_{self.latitude}_{self.longitude}"
            data = self.cache.get(
                cache_key,
                ttl_seconds=600,
                fetch_func=self._fetch_weather
            )
            if data:
                self.last_update = datetime.now()
                return True
            return False
        return self._fetch_weather() is not None

    def _fetch_weather(self) -> Optional[dict]:
        """Fetch weather from Open-Meteo API."""
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'current': 'temperature_2m,weather_code',
                'daily': 'temperature_2m_max,temperature_2m_min',
                'temperature_unit': 'fahrenheit' if self.units == 'fahrenheit' else 'celsius',
                'timezone': 'auto',
                'forecast_days': 1
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract current conditions
            current = data.get('current', {})
            self.temperature = round(current.get('temperature_2m', 0))
            self.weather_code = current.get('weather_code', 0)
            self.condition = self._get_condition(self.weather_code)

            # Extract today's high/low
            daily = data.get('daily', {})
            if daily.get('temperature_2m_max'):
                self.high = round(daily['temperature_2m_max'][0])
            if daily.get('temperature_2m_min'):
                self.low = round(daily['temperature_2m_min'][0])

            return data

        except Exception as e:
            print(f"Error fetching weather: {e}")
            return None

    def _get_condition(self, code: int) -> str:
        """Convert weather code to condition text."""
        conditions = {
            0: 'Clear',
            1: 'Mostly Clear',
            2: 'Partly Cloudy',
            3: 'Overcast',
            45: 'Foggy',
            48: 'Icy Fog',
            51: 'Light Drizzle',
            53: 'Drizzle',
            55: 'Heavy Drizzle',
            61: 'Light Rain',
            63: 'Rain',
            65: 'Heavy Rain',
            71: 'Light Snow',
            73: 'Snow',
            75: 'Heavy Snow',
            77: 'Snow Grains',
            80: 'Light Showers',
            81: 'Showers',
            82: 'Heavy Showers',
            85: 'Light Snow',
            86: 'Heavy Snow',
            95: 'Thunderstorm',
            96: 'Thunderstorm',
            99: 'Thunderstorm',
        }
        return conditions.get(code, 'Unknown')

    def render(self, renderer: Renderer, bounds: tuple) -> None:
        """Render compact weather in quadrant bounds."""
        x, y, width, height = bounds

        if self.temperature is None:
            self.update_data()

        center_x = x + width // 2
        center_y = y + height // 2

        # Weather icon (top, smaller to make room)
        if self.weather_code is not None:
            icon = self._get_weather_icon(self.weather_code)
            renderer.draw_text(
                icon,
                center_x,
                y + 8,
                font_size=12,
                anchor="mm"
            )

        # Temperature (large, centered)
        temp_str = f"{self.temperature}°" if self.temperature is not None else "--°"
        renderer.draw_text(
            temp_str,
            center_x,
            center_y - 2,
            font_size=18,
            bold=True,
            anchor="mm"
        )

        # High/Low (larger font, at bottom)
        if self.high is not None and self.low is not None:
            hl_str = f"H:{self.high}° L:{self.low}°"
            renderer.draw_text(
                hl_str,
                center_x,
                y + height - 6,
                font_size=12,
                bold=True,
                anchor="mm"
            )
