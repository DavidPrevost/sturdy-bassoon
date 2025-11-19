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
        """Fetch weather from Open-Meteo API with retry logic."""
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
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

                print(f"✓ Weather updated: {self.current_temp}° {self.current_condition}")
                return data

            except requests.exceptions.RequestException as e:
                print(f"Weather fetch attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print(f"✗ Weather fetch failed after {max_retries} attempts")
                    # Keep existing data if available, don't overwrite with None
                    return None
            except Exception as e:
                print(f"✗ Unexpected error fetching weather: {e}")
                return None

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
            # Show just the city name, truncate if too long
            city = self.location_name.split(',')[0]  # Remove state/country
            return city[:15]  # Limit to 15 chars
        elif self.zip_code:
            return self.zip_code
        else:
            return "Weather"  # Generic label instead of coordinates

    def render(self, renderer: Renderer, bounds: tuple) -> None:
        """Render weather widget."""
        x, y, width, height = bounds

        # Use temporary display values (don't permanently overwrite None)
        display_temp = self.current_temp if self.current_temp is not None else "--"
        display_condition = self.current_condition if self.current_condition is not None else "Unavailable"

        # Determine unit symbol
        unit = "°F" if self.units == 'fahrenheit' else "°C"

        # Layout: Current weather on left, forecast on right
        left_width = width // 2
        right_width = width - left_width

        # Draw current weather (left side)
        current_x = x + left_width // 2

        # Location name (larger, at top of left pane)
        location_display = self.get_location_display()
        renderer.draw_text(
            str(location_display),
            current_x,
            y + 8,
            font_size=11,
            bold=True,
            anchor="mm"
        )

        # ZIP code below location name
        if self.zip_code:
            renderer.draw_text(
                self.zip_code,
                current_x,
                y + 22,
                font_size=9,
                anchor="mm"
            )

        # Temperature (large, centered)
        temp_y = y + height // 2
        temp_text = f"{display_temp}{unit}"
        renderer.draw_text(
            temp_text,
            current_x,
            temp_y,
            font_size=18,
            bold=True,
            anchor="mm"
        )

        # Condition (below temperature)
        renderer.draw_text(
            str(display_condition),
            current_x,
            temp_y + 18,
            font_size=9,
            anchor="mm"
        )

        # Today's Hi/Lo at bottom of left pane
        if self.forecast:
            today_high = self.forecast[0][1]
            today_low = self.forecast[0][2]
            hilo_text = f"H:{today_high}° L:{today_low}°"
            renderer.draw_text(
                hilo_text,
                current_x,
                y + height - 8,
                font_size=9,
                bold=True,
                anchor="mm"
            )

        # Draw vertical separator
        separator_x = x + left_width
        renderer.draw_vertical_line(separator_x, thickness=1)

        # Draw forecast (right side) - skip today, show tomorrow onwards
        if self.forecast and len(self.forecast) > 1:
            forecast_x = x + left_width + 5
            forecast_start_y = y + 6

            # Skip today (index 0), show future days
            future_forecast = self.forecast[1:]

            # Calculate spacing for larger text
            available_height = height - 12
            line_height = available_height // len(future_forecast)

            for i, (day, high, low, condition) in enumerate(future_forecast):
                line_y = forecast_start_y + i * line_height

                # Day name (bold, larger)
                renderer.draw_text(
                    day[:3],
                    forecast_x,
                    line_y,
                    font_size=10,
                    bold=True,
                    anchor="lt"
                )

                # High/Low temps (larger)
                temp_text = f"{high}/{low}°"
                renderer.draw_text(
                    temp_text,
                    forecast_x + 30,
                    line_y,
                    font_size=10,
                    anchor="lt"
                )

                # Short condition (fits remaining space)
                short_cond = condition[:8] if len(condition) > 8 else condition
                renderer.draw_text(
                    short_cond,
                    forecast_x + 70,
                    line_y,
                    font_size=8,
                    anchor="lt"
                )
