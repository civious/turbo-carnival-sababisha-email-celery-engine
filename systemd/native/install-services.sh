#!/bin/bash
#
# Installation script for Sababisha Celery systemd services (Native - No Docker)
#

set -e

echo "=========================================="
echo "Installing Sababisha Celery Services (Native)"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "/opt/sababisha-celery/venv" ]; then
    echo "ERROR: Virtual environment not found at /opt/sababisha-celery/venv"
    echo "Please create it first:"
    echo "  cd /opt/sababisha-celery"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check if .env file exists
if [ ! -f "/opt/sababisha-celery/.env" ]; then
    echo "ERROR: .env file not found at /opt/sababisha-celery/.env"
    echo "Please create it with your configuration"
    exit 1
fi

# Copy service files to systemd directory
echo "1. Copying service files to /etc/systemd/system/..."
cp sababisha-celery-beat.service /etc/systemd/system/
cp sababisha-celery-worker.service /etc/systemd/system/
cp sababisha-celery-log-worker.service /etc/systemd/system/
cp sababisha-celery.target /etc/systemd/system/

echo "   ✓ Service files copied"
echo ""

# Reload systemd
echo "2. Reloading systemd daemon..."
systemctl daemon-reload
echo "   ✓ Systemd daemon reloaded"
echo ""

# Enable services
echo "3. Enabling services to start on boot..."
systemctl enable sababisha-celery-beat.service
systemctl enable sababisha-celery-worker.service
systemctl enable sababisha-celery-log-worker.service
systemctl enable sababisha-celery.target
echo "   ✓ Services enabled"
echo ""

echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Available commands:"
echo ""
echo "  Start all services:"
echo "    sudo systemctl start sababisha-celery.target"
echo ""
echo "  Stop all services:"
echo "    sudo systemctl stop sababisha-celery.target"
echo ""
echo "  Restart all services:"
echo "    sudo systemctl restart sababisha-celery.target"
echo ""
echo "  Check status:"
echo "    sudo systemctl status sababisha-celery-*"
echo ""
echo "  View logs:"
echo "    sudo journalctl -u sababisha-celery-beat -f"
echo "    sudo journalctl -u sababisha-celery-worker -f"
echo "    sudo journalctl -u sababisha-celery-log-worker -f"
echo ""
echo "  Individual service control:"
echo "    sudo systemctl restart sababisha-celery-beat"
echo "    sudo systemctl restart sababisha-celery-worker"
echo "    sudo systemctl restart sababisha-celery-log-worker"
echo ""
