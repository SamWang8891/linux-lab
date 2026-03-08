#!/bin/bash
# Linux Lab — One-click setup script
# Usage: sudo bash setup.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ─── Colors ──────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ─── Root check ──────────────────────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    err "請使用 sudo 執行此腳本"
    exit 1
fi

# ─── .env check ──────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    warn ".env 檔案不存在，從 .env.example 複製..."
    cp .env.example .env
    warn "請先編輯 .env 設定必要的參數（SECRET_KEY、ADMIN_PASSWORD、MAIL 等），然後重新執行此腳本。"
    exit 1
fi

source <(grep -v '^#' .env | sed 's/^/export /')
info "已載入 .env"

# ─── System packages ────────────────────────────────────────────────────
info "安裝系統套件..."
apt-get update
apt-get install -y \
    python3 python3-pip python3-venv \
    nginx \
    docker.io docker-compose-plugin \
    ebtables iptables \
    curl wget git

ok "系統套件安裝完成"

# ─── LXD / LXC ──────────────────────────────────────────────────────────
if ! command -v lxd &>/dev/null && ! command -v lxc &>/dev/null; then
    info "安裝 LXD..."
    snap install lxd
    lxd init --auto
fi

# Check if lab-net exists
if ! lxc network show lab-net &>/dev/null 2>&1; then
    info "設定 LXD 網路和 Profile..."
    bash scripts/setup_lxd.sh
    ok "LXD 設定完成"
else
    ok "LXD 網路 lab-net 已存在，跳過"
fi

# Verify profile has CPU limit
if lxc profile show lab-student &>/dev/null 2>&1; then
    info "確認 lab-student profile CPU 限制..."
    lxc profile set lab-student limits.cpu=1 2>/dev/null || true
    ok "Profile CPU 限制設為 1 核"
fi

# ─── Docker routing to LXD network ──────────────────────────────────────
info "設定 Docker → LXD 網路路由 (guacd 需要連到 10.99.0.0/24)..."
# Add route so Docker containers (guacd) can reach LXD containers
# Check if the route already exists
if ! ip route show | grep -q '10.99.0.0/24'; then
    ip route add 10.99.0.0/24 dev lxdbr0 2>/dev/null || \
    ip route add 10.99.0.0/24 dev lab-net 2>/dev/null || \
    warn "無法新增路由到 10.99.0.0/24，guacd 可能無法連到容器"
fi

# Allow forwarding from docker to lxd network
iptables -C FORWARD -i docker0 -o lxdbr0 -j ACCEPT 2>/dev/null || \
    iptables -I FORWARD -i docker0 -o lxdbr0 -j ACCEPT 2>/dev/null || true
iptables -C FORWARD -i lxdbr0 -o docker0 -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
    iptables -I FORWARD -i lxdbr0 -o docker0 -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true

ok "Docker ↔ LXD 路由設定完成"

# ─── Guacamole (Docker Compose) ─────────────────────────────────────────
info "啟動 Guacamole..."
bash scripts/setup_guac_db.sh
ok "Guacamole 啟動完成"

# ─── Python venv ─────────────────────────────────────────────────────────
info "建立 Python 虛擬環境..."
if [ ! -d venv ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
pip install -q werkzeug  # ensure latest
ok "Python 環境就緒"

# ─── Nginx ───────────────────────────────────────────────────────────────
info "設定 Nginx..."
cp nginx.conf /etc/nginx/sites-available/linux-lab
ln -sf /etc/nginx/sites-available/linux-lab /etc/nginx/sites-enabled/linux-lab
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
ok "Nginx 設定完成"

# ─── Systemd service ────────────────────────────────────────────────────
info "建立 systemd 服務..."
cat > /etc/systemd/system/linux-lab.service << EOF
[Unit]
Description=Linux Lab Flask App
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$SCRIPT_DIR
Environment=PATH=$SCRIPT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin
ExecStart=$SCRIPT_DIR/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable linux-lab
systemctl restart linux-lab
ok "linux-lab 服務已啟動"

# ─── Summary ─────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Linux Lab 安裝完成！${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo -e "  Flask App:   http://localhost:5000"
echo -e "  Guacamole:   http://localhost:8080/guacamole"
echo -e "  Nginx:       http://localhost (proxy → Flask + Guac)"
echo ""
echo -e "  管理員帳號:  ${ADMIN_EMAIL:-admin@example.com}"
echo -e "  管理員密碼:  (見 .env ADMIN_PASSWORD)"
echo ""
echo -e "  服務管理:"
echo -e "    systemctl status linux-lab"
echo -e "    systemctl restart linux-lab"
echo -e "    journalctl -u linux-lab -f"
echo ""
echo -e "  如需 HTTPS，建議在前面加 Nginx Proxy Manager 或 Caddy。"
echo ""
