#!/bin/bash
#
# Uninstallation script for Sababisha Celery systemd services (Native - No Docker)
#

set -e

echo "=========================================="
echo "Uninstalling Sababisha Celery Services (Native)"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

echo "1. Stopping all services..."
systemctl stop sababisha-celery.target 2>/dev/null || true
systemctl stop sababisha-celery-beat.service 2>/dev/null || true
systemctl stop sababisha-celery-worker.service 2>/dev/null || true
systemctl stop sababisha-celery-log-worker.service 2>/dev/null || true
echo "   ✓ Services stopped"
echo ""

echo "2. Disabling services..."
systemctl disable sababisha-celery-beat.service 2>/dev/null || true
systemctl disable sababisha-celery-worker.service 2>/dev/null || true
systemctl disable sababisha-celery-log-worker.service 2>/dev/null || true
systemctl disable sababisha-celery.target 2>/dev/null || true
echo "   ✓ Services disabled"
echo ""

echo "3. Removing service files..."
rm -f /etc/systemd/system/sababisha-celery-beat.service
rm -f /etc/systemd/system/sababisha-celery-worker.service
rm -f /etc/systemd/system/sababisha-celery-log-worker.service
rm -f /etc/systemd/system/sababisha-celery.target
echo "   ✓ Service files removed"
echo ""

echo "4. Reloading systemd daemon..."
systemctl daemon-reload
systemctl reset-failed 2>/dev/null || true
echo "   ✓ Systemd daemon reloaded"
echo ""

echo "=========================================="
echo "Uninstallation Complete!"
echo "=========================================="
echo ""
echo "Services have been completely removed."
echo ""
echo "To reinstall, run:"
echo "  sudo ./install-services.sh"
echo ""
