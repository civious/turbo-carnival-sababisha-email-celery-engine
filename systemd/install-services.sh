#!/bin/bash
#
# Installation script for Sababisha Celery systemd services
#

set -e

echo "=========================================="
echo "Installing Sababisha Celery Services"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

# Copy service files to systemd directory
echo "1. Copying service files to /etc/systemd/system/..."
cp sababisha-celery.service /etc/systemd/system/
cp sababisha-celery-beat.service /etc/systemd/system/
cp sababisha-celery-worker.service /etc/systemd/system/
cp sababisha-celery-log-worker.service /etc/systemd/system/

echo "   ✓ Service files copied"
echo ""

# Reload systemd
echo "2. Reloading systemd daemon..."
systemctl daemon-reload
echo "   ✓ Systemd daemon reloaded"
echo ""

# Enable services
echo "3. Enabling services to start on boot..."
systemctl enable sababisha-celery.service
echo "   ✓ Services enabled"
echo ""

echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Available commands:"
echo ""
echo "  Start all services:"
echo "    sudo systemctl start sababisha-celery"
echo ""
echo "  Stop all services:"
echo "    sudo systemctl stop sababisha-celery"
echo ""
echo "  Restart all services:"
echo "    sudo systemctl restart sababisha-celery"
echo ""
echo "  Check status:"
echo "    sudo systemctl status sababisha-celery"
echo ""
echo "  View logs:"
echo "    sudo journalctl -u sababisha-celery -f"
echo "    OR"
echo "    cd /opt/sababisha-celery && docker-compose logs -f"
echo ""
echo "  Disable auto-start on boot:"
echo "    sudo systemctl disable sababisha-celery"
echo ""
