# Web Dashboard

The e-ink dashboard includes a web-based control panel for easy configuration management.

## Features

- **Weather Location**: Change weather location using ZIP code
- **Portfolio Management**: Add/remove stock and crypto symbols
- **Settings**: Adjust refresh interval, temperature units, and display options
- **Live Configuration**: Changes are saved to config.yaml and applied on next refresh

## Starting the Web Dashboard

```bash
# Start the web server
python3 src/web/dashboard.py
```

The dashboard will be accessible at:
- **Local**: http://localhost:5000
- **Network**: http://<your-pi-ip>:5000

## Using the Dashboard

### Change Weather Location
1. Enter a 5-digit US ZIP code
2. Click "Update Location"
3. Weather will update with the new location on next refresh

### Manage Portfolio
1. Enter a stock symbol (e.g., AAPL) or crypto symbol (e.g., BTC-USD)
2. Click "Add Symbol"
3. Remove symbols by clicking the "Remove" button next to each

### Adjust Settings
- **Refresh Interval**: How often the display updates (1-60 minutes)
- **Temperature Units**: Fahrenheit or Celsius
- **Network Bandwidth**: Show/hide bandwidth monitoring

## Running as a Service

To keep the web dashboard running alongside the e-ink display:

```bash
# Create systemd service
sudo nano /etc/systemd/system/eink-web.service
```

```ini
[Unit]
Description=E-ink Dashboard Web Interface
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/sturdy-bassoon
ExecStart=/usr/bin/python3 /home/pi/sturdy-bassoon/src/web/dashboard.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable eink-web
sudo systemctl start eink-web
```

## Security Note

The web dashboard has no authentication and should only be run on trusted networks. For public access, consider adding authentication or using a reverse proxy with auth.

## API Endpoints

The dashboard provides a REST API that can be used programmatically:

- `GET /api/config` - Get full configuration
- `POST /api/weather/location` - Update weather location
- `GET /api/portfolio/symbols` - Get portfolio symbols
- `POST /api/portfolio/symbols` - Update all symbols
- `POST /api/portfolio/symbol` - Add a symbol
- `DELETE /api/portfolio/symbol/<symbol>` - Remove a symbol
- `POST /api/settings` - Update settings

Example:
```bash
curl -X POST http://localhost:5000/api/weather/location \
  -H "Content-Type: application/json" \
  -d '{"zip_code": "10001"}'
```
