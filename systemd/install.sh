#!/bin/bash
# Install systemd services for e-ink dashboard

echo "Installing e-ink dashboard services..."

# Copy service files
sudo cp eink-dashboard.service /etc/systemd/system/
sudo cp eink-web.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable eink-dashboard.service
sudo systemctl enable eink-web.service

# Start services
sudo systemctl start eink-dashboard.service
sudo systemctl start eink-web.service

echo ""
echo "Services installed and started!"
echo ""
echo "Commands:"
echo "  sudo systemctl status eink-dashboard   # Check display status"
echo "  sudo systemctl status eink-web         # Check web dashboard status"
echo "  sudo systemctl restart eink-dashboard  # Restart display"
echo "  sudo systemctl stop eink-dashboard     # Stop display"
echo "  sudo journalctl -u eink-dashboard -f   # View display logs"
echo ""
