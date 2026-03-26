#!/bin/bash
# ============================================================================
# Linux Lab — Nuke/Cleanup Script
# Run this as root inside the VM to clean up before exporting the OVA.
# ============================================================================
set -e

if [ "$EUID" -ne 0 ]; then
    echo "請使用 sudo 執行此腳本"
    exit 1
fi

echo "=== [1/5] Stopping services ==="
systemctl stop linux-lab.service || true
systemctl disable linux-lab.service || true
systemctl stop nginx || true
systemctl stop dnsmasq || true

echo "=== [2/5] Removing system configs ==="
rm -f /etc/systemd/system/linux-lab.service
rm -f /etc/systemd/system/lab-dns.service
rm -f /etc/nginx/sites-enabled/linux-lab
rm -f /etc/nginx/sites-available/linux-lab
rm -f /etc/dnsmasq.d/lab-override.conf
rm -f /usr/local/bin/reset-lab
systemctl daemon-reload

echo "=== [3/5] Cleaning up app and challenge files ==="
rm -rf /opt/linux-lab
rm -rf /home/user/challenges
rm -rf /home/user/documents
rm -rf /home/user/.config/autostart/quiz-browser.desktop
rm -rf /home/user/.config/autostart/konsole.desktop
rm -rf /home/user/.config/autostart/thunar.desktop

echo "=== [4/5] Clearing browser and system logs ==="
rm -rf /home/user/.mozilla
rm -rf /home/user/.cache
rm -rf /root/.cache
rm -rf /var/log/*
find /var/lib/apt/lists -type f -delete
apt-get clean

echo "=== [5/5] Finalizing shell history cleanup ==="
# This will take effect on next boot
cat /dev/null > /home/user/.bash_history
cat /dev/null > /root/.bash_history
history -c

echo ""
echo "==========================================="
echo "  🧹 Cleanup complete!"
echo "  The VM is now ready for export."
echo "==========================================="
