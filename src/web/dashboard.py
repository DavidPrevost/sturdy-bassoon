#!/usr/bin/env python3
"""Web dashboard for managing e-ink display settings."""
from flask import Flask, render_template, request, jsonify, redirect, url_for
import yaml
import os
from pathlib import Path

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.geocoding import Geocoder

app = Flask(__name__)

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"


def load_config():
    """Load configuration from YAML file."""
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)


def save_config(config):
    """Save configuration to YAML file."""
    with open(CONFIG_FILE, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


@app.route('/')
def index():
    """Main dashboard page."""
    config = load_config()
    return render_template('index.html', config=config)


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration."""
    config = load_config()
    return jsonify(config)


@app.route('/api/weather/location', methods=['POST'])
def update_weather_location():
    """Update weather location."""
    data = request.json
    config = load_config()

    if 'zip_code' in data:
        zip_code = data['zip_code']

        # Validate ZIP
        if not Geocoder.validate_zip(zip_code):
            return jsonify({'error': 'Invalid ZIP code'}), 400

        # Geocode
        result = Geocoder.zip_to_coords(zip_code)
        if not result:
            return jsonify({'error': 'ZIP code not found'}), 404

        lat, lon, city = result

        # Update config
        config['weather']['zip_code'] = zip_code
        config['weather']['latitude'] = lat
        config['weather']['longitude'] = lon
        config['weather']['location_name'] = city

        save_config(config)

        return jsonify({
            'success': True,
            'location': city,
            'latitude': lat,
            'longitude': lon
        })

    return jsonify({'error': 'Missing zip_code'}), 400


@app.route('/api/portfolio/symbols', methods=['GET'])
def get_portfolio_symbols():
    """Get current portfolio symbols."""
    config = load_config()
    symbols = config.get('portfolio', {}).get('symbols', [])
    return jsonify({'symbols': symbols})


@app.route('/api/portfolio/symbols', methods=['POST'])
def update_portfolio_symbols():
    """Update portfolio symbols."""
    data = request.json
    config = load_config()

    if 'symbols' in data:
        symbols = data['symbols']

        # Validate symbols (basic check)
        if not isinstance(symbols, list):
            return jsonify({'error': 'symbols must be a list'}), 400

        # Update config
        if 'portfolio' not in config:
            config['portfolio'] = {}

        config['portfolio']['symbols'] = symbols
        save_config(config)

        return jsonify({'success': True, 'symbols': symbols})

    return jsonify({'error': 'Missing symbols'}), 400


@app.route('/api/portfolio/symbol', methods=['POST'])
def add_portfolio_symbol():
    """Add a symbol to portfolio."""
    data = request.json
    config = load_config()

    if 'symbol' in data:
        symbol = data['symbol'].upper().strip()

        if not symbol:
            return jsonify({'error': 'Invalid symbol'}), 400

        # Add to config
        if 'portfolio' not in config:
            config['portfolio'] = {}
        if 'symbols' not in config['portfolio']:
            config['portfolio']['symbols'] = []

        if symbol not in config['portfolio']['symbols']:
            config['portfolio']['symbols'].append(symbol)
            save_config(config)

        return jsonify({'success': True, 'symbols': config['portfolio']['symbols']})

    return jsonify({'error': 'Missing symbol'}), 400


@app.route('/api/portfolio/symbol/<symbol>', methods=['DELETE'])
def remove_portfolio_symbol(symbol):
    """Remove a symbol from portfolio."""
    config = load_config()
    symbol = symbol.upper().strip()

    if 'portfolio' in config and 'symbols' in config['portfolio']:
        if symbol in config['portfolio']['symbols']:
            config['portfolio']['symbols'].remove(symbol)
            save_config(config)

    return jsonify({'success': True, 'symbols': config['portfolio'].get('symbols', [])})


@app.route('/api/portfolio/holdings', methods=['GET'])
def get_portfolio_holdings():
    """Get current portfolio holdings with shares and cost basis."""
    config = load_config()
    holdings = config.get('portfolio', {}).get('holdings', [])
    return jsonify({'holdings': holdings})


@app.route('/api/portfolio/holdings', methods=['POST'])
def update_portfolio_holdings():
    """Update all portfolio holdings."""
    data = request.json
    config = load_config()

    if 'holdings' in data:
        holdings = data['holdings']

        if not isinstance(holdings, list):
            return jsonify({'error': 'holdings must be a list'}), 400

        # Validate each holding
        for h in holdings:
            if 'symbol' not in h:
                return jsonify({'error': 'Each holding must have a symbol'}), 400
            h['symbol'] = h['symbol'].upper().strip()
            h['shares'] = float(h.get('shares', 0))
            h['cost_basis'] = float(h.get('cost_basis', 0))

        # Update config
        if 'portfolio' not in config:
            config['portfolio'] = {}

        config['portfolio']['holdings'] = holdings

        # Also update symbols list to match
        config['portfolio']['symbols'] = [h['symbol'] for h in holdings]

        save_config(config)

        return jsonify({'success': True, 'holdings': holdings})

    return jsonify({'error': 'Missing holdings'}), 400


@app.route('/api/portfolio/holding', methods=['POST'])
def add_portfolio_holding():
    """Add or update a single holding."""
    data = request.json
    config = load_config()

    if 'symbol' not in data:
        return jsonify({'error': 'Missing symbol'}), 400

    symbol = data['symbol'].upper().strip()
    shares = float(data.get('shares', 0))
    cost_basis = float(data.get('cost_basis', 0))

    if not symbol:
        return jsonify({'error': 'Invalid symbol'}), 400

    # Initialize if needed
    if 'portfolio' not in config:
        config['portfolio'] = {}
    if 'holdings' not in config['portfolio']:
        config['portfolio']['holdings'] = []
    if 'symbols' not in config['portfolio']:
        config['portfolio']['symbols'] = []

    # Check if symbol already exists
    existing = None
    for i, h in enumerate(config['portfolio']['holdings']):
        if h['symbol'] == symbol:
            existing = i
            break

    holding = {'symbol': symbol, 'shares': shares, 'cost_basis': cost_basis}

    if existing is not None:
        config['portfolio']['holdings'][existing] = holding
    else:
        config['portfolio']['holdings'].append(holding)
        if symbol not in config['portfolio']['symbols']:
            config['portfolio']['symbols'].append(symbol)

    save_config(config)

    return jsonify({'success': True, 'holdings': config['portfolio']['holdings']})


@app.route('/api/portfolio/holding/<symbol>', methods=['DELETE'])
def remove_portfolio_holding(symbol):
    """Remove a holding from portfolio."""
    config = load_config()
    symbol = symbol.upper().strip()

    if 'portfolio' in config:
        # Remove from holdings
        if 'holdings' in config['portfolio']:
            config['portfolio']['holdings'] = [
                h for h in config['portfolio']['holdings']
                if h['symbol'] != symbol
            ]

        # Remove from symbols
        if 'symbols' in config['portfolio'] and symbol in config['portfolio']['symbols']:
            config['portfolio']['symbols'].remove(symbol)

        save_config(config)

    return jsonify({'success': True, 'holdings': config['portfolio'].get('holdings', [])})


@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update general settings."""
    data = request.json
    config = load_config()

    # Update refresh interval
    if 'refresh_interval' in data:
        interval = int(data['refresh_interval'])
        if interval < 1 or interval > 60:
            return jsonify({'error': 'Interval must be 1-60 minutes'}), 400
        config['refresh']['interval_minutes'] = interval

    # Update clock update interval
    if 'clock_update_seconds' in data:
        seconds = int(data['clock_update_seconds'])
        if seconds < 10 or seconds > 300:
            return jsonify({'error': 'Clock update must be 10-300 seconds'}), 400
        config['refresh']['clock_update_seconds'] = seconds

    # Update weather units
    if 'weather_units' in data:
        units = data['weather_units']
        if units not in ['fahrenheit', 'celsius']:
            return jsonify({'error': 'Invalid units'}), 400
        config['weather']['units'] = units

    # Update weather forecast days
    if 'weather_forecast_days' in data:
        days = int(data['weather_forecast_days'])
        if days < 1 or days > 7:
            return jsonify({'error': 'Forecast days must be 1-7'}), 400
        config['weather']['show_forecast_days'] = days

    # Update network settings
    if 'network_show_bandwidth' in data:
        config['network']['show_bandwidth'] = bool(data['network_show_bandwidth'])

    if 'network_show_devices' in data:
        config['network']['show_devices'] = bool(data['network_show_devices'])

    save_config(config)
    return jsonify({'success': True})


@app.route('/api/news/settings', methods=['GET'])
def get_news_settings():
    """Get news widget settings."""
    config = load_config()
    news = config.get('news', {})
    return jsonify({
        'max_headlines': news.get('max_headlines', 5),
        'feed_url': news.get('feed_url', 'https://news.ycombinator.com/rss'),
        'feed_name': news.get('feed_name', 'Hacker News'),
        'feeds': news.get('feeds', [])
    })


@app.route('/api/news/settings', methods=['POST'])
def update_news_settings():
    """Update news widget settings."""
    data = request.json
    config = load_config()

    if 'news' not in config:
        config['news'] = {}

    # Update max headlines
    if 'max_headlines' in data:
        headlines = int(data['max_headlines'])
        if headlines < 1 or headlines > 10:
            return jsonify({'error': 'Headlines must be 1-10'}), 400
        config['news']['max_headlines'] = headlines

    # Update single feed (simple mode)
    if 'feed_url' in data:
        config['news']['feed_url'] = data['feed_url'].strip()
    if 'feed_name' in data:
        config['news']['feed_name'] = data['feed_name'].strip()

    save_config(config)
    return jsonify({'success': True})


@app.route('/api/news/feeds', methods=['GET'])
def get_news_feeds():
    """Get list of RSS feeds."""
    config = load_config()
    feeds = config.get('news', {}).get('feeds', [])
    # Also include the single feed if it exists
    single_url = config.get('news', {}).get('feed_url')
    single_name = config.get('news', {}).get('feed_name')
    return jsonify({
        'feeds': feeds,
        'single_feed': {'url': single_url, 'name': single_name} if single_url else None
    })


@app.route('/api/news/feed', methods=['POST'])
def add_news_feed():
    """Add a new RSS feed."""
    data = request.json
    config = load_config()

    if 'url' not in data or 'name' not in data:
        return jsonify({'error': 'Missing url or name'}), 400

    url = data['url'].strip()
    name = data['name'].strip()

    if not url or not name:
        return jsonify({'error': 'URL and name are required'}), 400

    if 'news' not in config:
        config['news'] = {}
    if 'feeds' not in config['news']:
        config['news']['feeds'] = []

    # Check for duplicate URL
    for feed in config['news']['feeds']:
        if feed.get('url') == url:
            return jsonify({'error': 'Feed URL already exists'}), 400

    config['news']['feeds'].append({'url': url, 'name': name})
    save_config(config)

    return jsonify({'success': True, 'feeds': config['news']['feeds']})


@app.route('/api/news/feed', methods=['DELETE'])
def remove_news_feed():
    """Remove an RSS feed by URL."""
    data = request.json
    config = load_config()

    if 'url' not in data:
        return jsonify({'error': 'Missing url'}), 400

    url = data['url'].strip()

    if 'news' in config and 'feeds' in config['news']:
        config['news']['feeds'] = [
            f for f in config['news']['feeds'] if f.get('url') != url
        ]
        save_config(config)

    return jsonify({'success': True, 'feeds': config['news'].get('feeds', [])})


def main():
    """Run the web dashboard."""
    print("Starting web dashboard...")
    print(f"Config file: {CONFIG_FILE}")
    print("\nAccess the dashboard at: http://localhost:5000")
    print("Or from another device: http://<pi-ip-address>:5000")
    print("\nPress Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == '__main__':
    main()
