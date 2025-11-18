# E-ink Dashboard for Raspberry Pi

A modular, low-power dashboard for Raspberry Pi with e-ink touch display. Displays weather, time, and more on a 250×122 pixel e-paper screen.

## Features

### Current
- **Clock Widget**: Current time and date
- **Weather Widget**: Current conditions and 3-day forecast using Open-Meteo API
- **Portfolio Widget**: Track stocks and cryptocurrency prices with % change
- **Network Monitor**: Real-time bandwidth usage and network statistics (Phase 3)
  - Upload/download speeds
  - Total bytes sent/received
  - Auto-detects active network interface
- **Multi-screen Navigation**: Swipe between different dashboard screens
- **Touch Support**: Framework for gesture-based navigation
- **Configurable refresh**: Default 15-minute updates
- **Low power**: E-ink display with minimal standby consumption
- **Two display modes**: Multi-screen or single-screen layout

### Planned (Future Enhancements)
- **Hardware touch integration**: Full touch support for Waveshare touch controller
- **Additional widgets**: Calendar, tasks, system stats, RSS feeds
- **Advanced network features**: Connected devices, Pi-hole integration
- **Customization**: Themes, widget positioning, more layout options

## Hardware Requirements

- Raspberry Pi Zero 2 W (or similar)
- Waveshare 2.13" e-Paper HAT with touch (250×122 pixels)
- microSD card with Raspberry Pi OS

## Installation

### 1. Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-pil python3-numpy git

# Enable SPI interface (required for e-ink display)
sudo raspi-config
# Navigate to: Interface Options → SPI → Enable
# Reboot when prompted
```

### 2. Install Waveshare E-Paper Library

```bash
# Clone Waveshare library
cd ~
git clone https://github.com/waveshare/e-Paper.git

# Install Python library
cd e-Paper/RaspberryPi_JetsonNano/python
sudo python3 setup.py install
```

### 3. Install Dashboard Application

```bash
# Clone this repository
cd ~
git clone <repository-url> sturdy-bassoon
cd sturdy-bassoon

# Install Python dependencies
pip3 install -r requirements.txt
```

### 4. Configure Your Location

Edit `config/config.yaml` and set your latitude/longitude:

```yaml
weather:
  latitude: 40.7128   # Change to your latitude
  longitude: -74.0060  # Change to your longitude
  units: fahrenheit    # or celsius
```

You can find your coordinates at [latlong.net](https://www.latlong.net/)

## Usage

### Run Dashboard

```bash
# Run in foreground (for testing)
python3 src/main.py

# Run once and exit (useful for debugging)
python3 src/main.py --once

# Run with custom config
python3 src/main.py --config /path/to/config.yaml
```

### Run as System Service (Auto-start on Boot)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/eink-dashboard.service
```

Paste the following (adjust paths if needed):

```ini
[Unit]
Description=E-ink Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/sturdy-bassoon
ExecStart=/usr/bin/python3 /home/pi/sturdy-bassoon/src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable eink-dashboard

# Start service now
sudo systemctl start eink-dashboard

# Check status
sudo systemctl status eink-dashboard

# View logs
journalctl -u eink-dashboard -f
```

## Configuration

Edit `config/config.yaml` to customize:

```yaml
# Display settings
display:
  width: 250
  height: 122
  rotation: 0  # 0, 90, 180, 270
  multi_screen_mode: true  # Enable multi-screen navigation

# Touch input (set enabled: true when hardware is available)
touch:
  enabled: false

# Update frequency
refresh:
  interval_minutes: 15  # How often to update

# Multi-screen mode: Define screens with widgets
screens:
  - name: home
    widgets:
      - clock
      - weather
  - name: portfolio
    widgets:
      - portfolio
  - name: network
    widgets:
      - network

# Single-screen mode: List all widgets (used if multi_screen_mode: false)
widgets:
  - clock
  - weather

# Widget-specific settings
weather:
  latitude: 40.7128
  longitude: -74.0060
  units: fahrenheit  # fahrenheit or celsius
  show_forecast_days: 3

portfolio:
  show_change: true  # Show percentage change
  symbols:
    - AAPL
    - GOOGL
    - BTC-USD
    - ETH-USD

network:
  show_bandwidth: true
  show_devices: false
  interface: null  # Auto-detect, or specify "wlan0", "eth0", etc.
```

### Display Modes

**Multi-screen Mode** (default): Each screen is a separate page you can navigate between by swiping or tapping the edges. This is ideal for organizing different types of information.

**Single-screen Mode**: All widgets are displayed on one screen, split vertically. Set `display.multi_screen_mode: false` to use this mode.

## Project Structure

```
sturdy-bassoon/
├── src/
│   ├── main.py              # Main application
│   ├── display/
│   │   ├── driver.py        # E-ink hardware interface
│   │   ├── renderer.py      # Drawing utilities
│   │   └── screen_manager.py  # Multi-screen navigation
│   ├── widgets/
│   │   ├── base.py          # Base widget class
│   │   ├── clock.py         # Clock widget
│   │   ├── weather.py       # Weather widget
│   │   ├── portfolio.py     # Portfolio tracker widget
│   │   └── network.py       # Network monitor widget
│   ├── touch/
│   │   └── handler.py       # Touch input handling
│   └── utils/
│       ├── config.py        # Configuration management
│       └── api_cache.py     # API caching
├── config/
│   └── config.yaml          # Configuration file
└── .cache/                  # Cache directory (auto-created)
```

## Development

### Simulation Mode

If you're developing without the hardware, the display driver will automatically enter simulation mode and save rendered images to `.cache/display_output.png`.

### Adding New Widgets

1. Create a new file in `src/widgets/`
2. Inherit from `Widget` base class
3. Implement `update_data()` and `render()` methods
4. Register in `src/main.py` widget registry
5. Add configuration options to `config/config.yaml`

Example widget skeleton:

```python
from .base import Widget
from src.display.renderer import Renderer

class MyWidget(Widget):
    def update_data(self) -> bool:
        # Fetch/update data
        return True

    def render(self, renderer: Renderer, bounds: tuple) -> None:
        x, y, width, height = bounds
        # Draw widget content
        renderer.draw_text("Hello", x + 10, y + 10)
```

## Troubleshooting

### Display not working
- Ensure SPI is enabled: `ls /dev/spidev*` should show devices
- Check connections between display and Pi
- Try running with `sudo` to rule out permission issues

### API errors
- Check internet connection: `ping api.open-meteo.com`
- Verify latitude/longitude in config
- Check cache directory permissions

### Service not starting
- Check logs: `journalctl -u eink-dashboard -n 50`
- Verify file paths in service file
- Ensure Python dependencies are installed

## APIs Used

- **Weather**: [Open-Meteo](https://open-meteo.com/) - Free, no API key required
- **Stocks**: [yfinance](https://github.com/ranaroussi/yfinance) - Free, Yahoo Finance data
- **Crypto**: [CoinGecko](https://www.coingecko.com/en/api) - Free tier, no API key required

## License

MIT License - Feel free to modify and use for your own projects!

## Credits

- Waveshare for e-Paper HAT libraries
- Open-Meteo for weather data
- Built with Python, Pillow, and lots of coffee
