"""Weather widget using Open-Meteo API."""
import requests
from datetime import datetime
from .base import Widget
from src.display.renderer import Renderer
from src.utils.geocoding import Geocoder


class WeatherWidget(Widget):
    """Displays current weather and forecast."""

    # Weather code to description mapping (WMO Weather interpretation codes)
    WEATHER_CODES = {
        0: "Clear",
        1: "Mainly Clear",
        2: "Partly Cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Foggy",
        51: "Light Drizzle",
        53: "Drizzle",
        55: "Heavy Drizzle",
        61: "Light Rain",
        63: "Rain",
        65: "Heavy Rain",
        71: "Light Snow",
        73: "Snow",
        75: "Heavy Snow",
        77: "Snow Grains",
        80: "Light Showers",
        81: "Showers",
        82: "Heavy Showers",
        85: "Snow Showers",
        86: "Heavy Snow Showers",
        95: "Thunderstorm",
        96: "Thunderstorm + Hail",
        99: "Heavy Thunderstorm"
    }

    def __init__(self, config, cache=None):
        super().__init__(config, cache)

        # Support both ZIP code and lat/long
        self.zip_code = config.get('weather.zip_code', None)
        self.latitude = config.get('weather.latitude', 40.7128)
        self.longitude = config.get('weather.longitude', -74.0060)
        self.location_name = config.get('weather.location_name', None)

        # If ZIP code is provided, geocode it
        if self.zip_code and Geocoder.validate_zip(self.zip_code):
            self.set_location_from_zip(self.zip_code)

        self.units = config.get('weather.units', 'fahrenheit')
        self.forecast_days = config.get('weather.show_forecast_days', 3)

        self.current_temp = None
        self.current_condition = None
        self.forecast = []  # List of (day, high, low, condition) tuples

    def update_data(self) -> bool:
        """Fetch weather data from Open-Meteo API."""
        if self.cache is None:
            return self._fetch_weather()

        # Cache for 10 minutes
        cache_key = f"weather_{self.latitude}_{self.longitude}"
        data = self.cache.get(
            cache_key,
            ttl_seconds=600,  # 10 minutes
            fetch_func=self._fetch_weather
        )

        if data:
            self.last_update = datetime.now()
            return True
        return False

    def _fetch_weather(self) -> dict:
        """Fetch weather from Open-Meteo API."""
        try:
            # Determine temperature unit
            temp_unit = 'fahrenheit' if self.units == 'fahrenheit' else 'celsius'

            # Build API URL
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'current': ['temperature_2m', 'weather_code'],
                'daily': ['temperature_2m_max', 'temperature_2m_min', 'weather_code'],
                'temperature_unit': temp_unit,
                'timezone': 'auto',
                'forecast_days': self.forecast_days
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse current weather
            self.current_temp = round(data['current']['temperature_2m'])
            weather_code = data['current']['weather_code']
            self.current_condition = self.WEATHER_CODES.get(weather_code, "Unknown")

            # Parse forecast
            self.forecast = []
            daily = data['daily']
            for i in range(min(self.forecast_days, len(daily['time']))):
                date = datetime.fromisoformat(daily['time'][i])
                day_name = date.strftime("%a") if i > 0 else "Today"
                high = round(daily['temperature_2m_max'][i])
                low = round(daily['temperature_2m_min'][i])
                code = daily['weather_code'][i]
                condition = self.WEATHER_CODES.get(code, "Unknown")

                self.forecast.append((day_name, high, low, condition))

            print(f"Weather updated: {self.current_temp}° {self.current_condition}")
            return data

        except Exception as e:
            print(f"Error fetching weather: {e}")
            # Set fallback values
            self.current_temp = self.current_temp or "--"
            self.current_condition = self.current_condition or "Unavailable"
            return None

    def set_location_from_zip(self, zip_code: str) -> bool:
        """
        Set location using ZIP code.

        Args:
            zip_code: 5-digit US ZIP code

        Returns:
            True if successful
        """
        if not Geocoder.validate_zip(zip_code):
            print(f"Invalid ZIP code: {zip_code}")
            return False

        result = Geocoder.zip_to_coords(zip_code)
        if result:
            lat, lon, city = result
            self.latitude = lat
            self.longitude = lon
            self.zip_code = zip_code
            self.location_name = city

            # Clear cache to force refresh
            if self.cache:
                cache_key = f"weather_{self.latitude}_{self.longitude}"
                self.cache.clear(cache_key)

            print(f"Location set to {city} (ZIP {zip_code})")
            return True

        return False

    def get_location_display(self) -> str:
        """Get location string for display."""
        if self.location_name:
            return self.location_name
        elif self.zip_code:
            return f"ZIP {self.zip_code}"
        else:
            return f"{self.latitude:.2f}, {self.longitude:.2f}"

    def render(self, renderer: Renderer, bounds: tuple) -> None:
        """Render weather widget."""
        x, y, width, height = bounds

        if self.current_temp is None:
            self.update_data()

        # Determine unit symbol
        unit = "°F" if self.units == 'fahrenheit' else "°C"

        # Draw location name at top
        location_display = self.get_location_display()
        renderer.draw_text(
            location_display,
            x + width // 2,
            y + 3,
            font_size=9,
            anchor="mt"
        )

        # Layout: Current weather on left, forecast on right
        left_width = width // 2
        right_width = width - left_width

        # Draw current weather (left side)
        current_x = x + left_width // 2
        temp_y = y + height // 3 + 5  # Shift down to make room for location

        # Temperature (large)
        temp_text = f"{self.current_temp}{unit}"
        renderer.draw_text(
            temp_text,
            current_x,
            temp_y,
            font_size=20,
            bold=True,
            anchor="mm"
        )

        # Condition (below temperature)
        condition_y = temp_y + 22
        renderer.draw_text(
            self.current_condition,
            current_x,
            condition_y,
            font_size=9,
            anchor="mm"
        )

        # Draw vertical separator
        separator_x = x + left_width
        renderer.draw_vertical_line(separator_x, thickness=1)

        # Draw forecast (right side)
        if self.forecast:
            forecast_x = x + left_width + 5
            forecast_start_y = y + 10
            line_height = (height - 20) // len(self.forecast)

            for i, (day, high, low, condition) in enumerate(self.forecast):
                line_y = forecast_start_y + i * line_height

                # Day name
                renderer.draw_text(
                    day,
                    forecast_x,
                    line_y,
                    font_size=10,
                    bold=True,
                    anchor="lt"
                )

                # High/Low temps
                temp_text = f"{high}°/{low}°"
                renderer.draw_text(
                    temp_text,
                    forecast_x,
                    line_y + 12,
                    font_size=9,
                    anchor="lt"
                )
