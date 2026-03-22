#!/bin/bash
# Packer provisioner — runs as root inside the VM after Debian install
set -e

export DEBIAN_FRONTEND=noninteractive

# ── System packages ──────────────────────────────────────────────────────
apt-get update
apt-get install -y --no-install-recommends \
    nginx python3 python3-venv python3-pip \
    xfce4 xfce4-terminal xfce4-goodies lightdm \
    firefox-esr dbus-x11 \
    nano vim curl wget man-db dnsutils \
    net-tools iproute2 procps htop \
    unzip xz-utils file \
    locales sudo

# Generate zh_TW locale
sed -i 's/# zh_TW.UTF-8/zh_TW.UTF-8/' /etc/locale.gen
locale-gen

# ── Auto-login for LightDM ──────────────────────────────────────────────
mkdir -p /etc/lightdm/lightdm.conf.d
cat > /etc/lightdm/lightdm.conf.d/50-autologin.conf << 'EOF'
[Seat:*]
autologin-user=user
autologin-user-timeout=0
EOF

# ── Auto-start Firefox on login ─────────────────────────────────────────
mkdir -p /home/user/.config/autostart
cat > /home/user/.config/autostart/quiz-browser.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Linux Lab Quiz
Exec=firefox-esr http://localhost
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
chown -R user:user /home/user/.config

# ── DNS challenge: override foo.com locally ──────────────────────────────
apt-get install -y --no-install-recommends dnsmasq
cat > /etc/dnsmasq.d/lab-override.conf << 'DNSCONF'
# Override foo.com to return 0.0.0.0
address=/foo.com/0.0.0.0
# Forward everything else to Cloudflare
server=1.1.1.1
DNSCONF
# Point resolv.conf to local dnsmasq
echo "nameserver 127.0.0.1" > /etc/resolv.conf.lab

# Systemd service to apply DNS config after boot
cat > /etc/systemd/system/lab-dns.service << 'EOF'
[Unit]
Description=Set lab DNS config
After=network-online.target dnsmasq.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/cp /etc/resolv.conf.lab /etc/resolv.conf
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
systemctl enable lab-dns.service
systemctl enable dnsmasq

# ── Setup challenge files ────────────────────────────────────────────────
CHAL_DIR="/home/user/challenges"
mkdir -p "$CHAL_DIR"
mkdir -p /home/user/documents

# Q6: Hidden file (ls -a)
echo "FLAG{ls_master}" > "$CHAL_DIR/.secret_flag"

# Q8: File to edit
echo "Change this text" > "$CHAL_DIR/edit_me.txt"

# Q10: Files/dirs to delete
echo "Delete this file!" > "$CHAL_DIR/delete_me.txt"
mkdir -p "$CHAL_DIR/remove_this_dir"
echo "remove me" > "$CHAL_DIR/remove_this_dir/file.txt"
mkdir -p "$CHAL_DIR/protected_dir"
echo "protected" > "$CHAL_DIR/protected_dir/secret.txt"
chown -R root:root "$CHAL_DIR/protected_dir"

# Q11: Files/dirs to copy
echo "I am the original file." > "$CHAL_DIR/original.txt"
mkdir -p "$CHAL_DIR/sample_dir"
echo "sample file 1" > "$CHAL_DIR/sample_dir/file1.txt"
echo "sample file 2" > "$CHAL_DIR/sample_dir/file2.txt"

# Q12: Files to move/rename
echo "Move me to another location!" > "$CHAL_DIR/move_me.txt"
echo "Rename me to something else!" > "$CHAL_DIR/rename_me.txt"
mkdir -p "$CHAL_DIR/moved"

# Q13: Hidden treasure
mkdir -p /var/lib
echo "FLAG{treasure_found}" > /var/lib/hidden_treasure.txt

# Q18: Compress/extract challenges
mkdir -p "$CHAL_DIR/compress_me"
echo "file to compress 1" > "$CHAL_DIR/compress_me/data1.txt"
echo "file to compress 2" > "$CHAL_DIR/compress_me/data2.txt"
mkdir -p /tmp/extract_content
echo "extracted file 1" > /tmp/extract_content/extracted1.txt
echo "extracted file 2" > /tmp/extract_content/extracted2.txt
(cd /tmp && tar czf "$CHAL_DIR/extract_me.tar.gz" extract_content/)
rm -rf /tmp/extract_content

# Q19-21: Script file (root-owned, not executable)
cat > "$CHAL_DIR/22.sh" << 'SCRIPT'
#!/bin/bash
echo "This is GDG NTUST."
SCRIPT
chmod 644 "$CHAL_DIR/22.sh"
chown root:root "$CHAL_DIR/22.sh"

# Set ownership
chown user:user "$CHAL_DIR"
chown user:user "$CHAL_DIR/.secret_flag"
chown user:user "$CHAL_DIR/edit_me.txt"
chown user:user "$CHAL_DIR/delete_me.txt"
chown -R user:user "$CHAL_DIR/remove_this_dir"
chown user:user "$CHAL_DIR/original.txt"
chown -R user:user "$CHAL_DIR/sample_dir"
chown user:user "$CHAL_DIR/move_me.txt"
chown user:user "$CHAL_DIR/rename_me.txt"
chown -R user:user "$CHAL_DIR/moved"
chown -R user:user "$CHAL_DIR/compress_me"
chown user:user "$CHAL_DIR/extract_me.tar.gz"
chown user:user /home/user/.bashrc
chown -R user:user /home/user/documents

# ── Also create the reset script for challenges ─────────────────────────
cp /opt/linux-lab/scripts/reset_challenges.sh /usr/local/bin/reset-lab
chmod +x /usr/local/bin/reset-lab

# ── Flask app (local version) ───────────────────────────────────────────
cd /opt/linux-lab
python3 -m venv venv
/opt/linux-lab/venv/bin/pip install flask flask-sqlalchemy flask-wtf gunicorn

# Initialize the DB
/opt/linux-lab/venv/bin/python -c "
from app_local import app, init_db
with app.app_context():
    init_db()
"

# ── Systemd service for the Flask app ────────────────────────────────────
cat > /etc/systemd/system/linux-lab.service << 'EOF'
[Unit]
Description=Linux Lab Quiz App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/linux-lab
ExecStart=/opt/linux-lab/venv/bin/gunicorn -w 1 -b 127.0.0.1:5000 app_local:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable linux-lab.service

# ── Nginx config ─────────────────────────────────────────────────────────
rm -f /etc/nginx/sites-enabled/default
cp /tmp/linux-lab-nginx.conf /etc/nginx/sites-available/linux-lab
ln -sf /etc/nginx/sites-available/linux-lab /etc/nginx/sites-enabled/linux-lab
systemctl enable nginx

# ── Lock root SSH (was only for Packer) ──────────────────────────────────
passwd -l root
sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config

# ── Process limits ───────────────────────────────────────────────────────
cat >> /etc/security/limits.conf << 'LIMITS'
*    hard    nproc    300
*    soft    nproc    300
LIMITS

# ── Clean up ─────────────────────────────────────────────────────────────
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "=== VM provisioning complete ==="
