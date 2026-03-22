#!/bin/bash
# Nuclear reset — delete ALL lab resources and start fresh
# Usage: sudo bash scripts/nuke.sh
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}╔══════════════════════════════════════════╗${NC}"
echo -e "${RED}║  ⚠️  NUCLEAR RESET — DESTROYS EVERYTHING  ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "This will delete:"
echo "  - All LXD containers (lab-student-*)"
echo "  - LXD profile (lab-student)"
echo "  - LXD network (lab-net)"
echo "  - LXD storage pool (default)"
echo "  - All lab iptables rules"
echo "  - Guacamole Docker containers + DB"
echo "  - Flask database"
echo "  - systemd service"
echo ""
read -p "Type 'YES' to confirm: " confirm
if [ "$confirm" != "YES" ]; then
    echo "Aborted."
    exit 1
fi

echo ""

# ─── Stop services ──────────────────────────────────────────────────────
echo -e "${YELLOW}[1/7] Stopping services...${NC}"
systemctl stop linux-lab 2>/dev/null || true
systemctl disable linux-lab 2>/dev/null || true
rm -f /etc/systemd/system/linux-lab.service
rm -f /etc/systemd/system/lab-iptables.service
systemctl daemon-reload

# ─── Delete all LXD containers ──────────────────────────────────────────
echo -e "${YELLOW}[2/7] Deleting LXD containers...${NC}"
for c in $(lxc list --format=csv -c n 2>/dev/null); do
    echo "  Deleting $c..."
    lxc delete "$c" --force 2>/dev/null || true
done

# ─── Delete LXD profile ─────────────────────────────────────────────────
echo -e "${YELLOW}[3/7] Removing LXD profile and network...${NC}"
lxc profile delete lab-student 2>/dev/null || true
lxc network delete lab-net 2>/dev/null || true
lxc storage delete default 2>/dev/null || true

# ─── Delete Guacamole Docker ────────────────────────────────────────────
echo -e "${YELLOW}[4/7] Stopping Guacamole Docker containers...${NC}"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"
docker compose -f docker-compose.guac.yml down -v 2>/dev/null || true
docker-compose -f docker-compose.guac.yml down -v 2>/dev/null || true

# ─── Flush iptables rules ───────────────────────────────────────────────
echo -e "${YELLOW}[5/7] Flushing lab iptables rules...${NC}"
iptables -F LAB_HOST_FILTER 2>/dev/null || true
iptables -X LAB_HOST_FILTER 2>/dev/null || true

# Remove all lab-related INPUT rules
for BRIF in lxdbr0 lab-net; do
    iptables -D INPUT -i $BRIF -d 10.99.0.1 -j LAB_HOST_FILTER 2>/dev/null || true
    iptables -D INPUT -i $BRIF -d 255.255.255.255 -p udp --dport 67 -j ACCEPT 2>/dev/null || true
    iptables -D INPUT -i $BRIF ! -d 10.99.0.0/24 -j DROP 2>/dev/null || true
    iptables -D FORWARD -i docker0 -o $BRIF -j ACCEPT 2>/dev/null || true
    iptables -D FORWARD -i $BRIF -o docker0 -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
    iptables -D FORWARD -i $BRIF -o $BRIF -j DROP 2>/dev/null || true
done
iptables -D FORWARD -s 10.99.0.0/24 -d 169.254.169.254 -j DROP 2>/dev/null || true
rm -f /etc/iptables/rules.v4

# ─── Delete Flask DB ────────────────────────────────────────────────────
echo -e "${YELLOW}[6/7] Removing Flask database...${NC}"
rm -f "$SCRIPT_DIR/instance/linux_lab.db" 2>/dev/null || true
rm -f "$SCRIPT_DIR/linux_lab.db" 2>/dev/null || true

# ─── Clean Nginx ────────────────────────────────────────────────────────
echo -e "${YELLOW}[7/7] Removing Nginx config...${NC}"
rm -f /etc/nginx/sites-enabled/linux-lab
rm -f /etc/nginx/sites-available/linux-lab
systemctl reload nginx 2>/dev/null || true

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Nuclear reset complete!               ║${NC}"
echo -e "${GREEN}║  Run: sudo bash setup.sh                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
