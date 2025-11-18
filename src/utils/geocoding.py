"""Geocoding utilities for converting ZIP codes to coordinates."""
import requests
from typing import Optional, Tuple


class Geocoder:
    """Handle geocoding operations (ZIP to lat/long)."""

    @staticmethod
    def zip_to_coords(zip_code: str) -> Optional[Tuple[float, float, str]]:
        """
        Convert US ZIP code to latitude/longitude.

        Args:
            zip_code: 5-digit ZIP code

        Returns:
            Tuple of (latitude, longitude, city_name) or None if lookup fails
        """
        try:
            # Use OpenStreetMap Nominatim (free, no API key)
            # Rate limit: 1 request/second
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'postalcode': zip_code,
                'country': 'US',
                'format': 'json',
                'limit': 1
            }
            headers = {
                'User-Agent': 'RaspberryPi-EInk-Dashboard/1.0'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data and len(data) > 0:
                result = data[0]
                lat = float(result['lat'])
                lon = float(result['lon'])

                # Extract city name from display_name
                # Usually format: "City, County, State, ZIP, Country"
                display_parts = result.get('display_name', '').split(',')
                city = display_parts[0].strip() if display_parts else f"ZIP {zip_code}"

                print(f"Geocoded {zip_code} -> {lat}, {lon} ({city})")
                return lat, lon, city

            print(f"No results for ZIP code: {zip_code}")
            return None

        except Exception as e:
            print(f"Error geocoding ZIP {zip_code}: {e}")
            return None

    @staticmethod
    def validate_zip(zip_code: str) -> bool:
        """
        Validate US ZIP code format.

        Args:
            zip_code: String to validate

        Returns:
            True if valid 5-digit ZIP
        """
        if not zip_code:
            return False

        # Remove any whitespace
        zip_code = zip_code.strip()

        # Must be exactly 5 digits
        if len(zip_code) != 5:
            return False

        # Must be all digits
        return zip_code.isdigit()
