#!/bin/bash
# Initialize a student container with challenge files
# Usage: lxc exec <container> -- bash < init_container.sh

set -e

# Update and install essentials
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
    openssh-server sudo nano vim curl wget \
    net-tools iproute2 procps htop \
    unzip xz-utils file \
    pcmanfm lxterminal openbox xrdp xorgxrdp dbus-x11 \
    locales

# Generate locale
sed -i 's/# zh_TW.UTF-8/zh_TW.UTF-8/' /etc/locale.gen
locale-gen

# Create student user
useradd -m -s /bin/bash user
echo "user:user" | chpasswd
usermod -aG sudo user

# Install and configure UFW — block SSH from lab-net (inter-container)
apt-get install -y --no-install-recommends ufw
ufw default allow incoming
# Block SSH from other containers on lab-net, allow from gateway (10.99.0.1)
ufw allow from 10.99.0.1 to any port 22 proto tcp
ufw deny from 10.99.0.0/24 to any port 22 proto tcp
ufw --force enable

# Enable services
systemctl enable ssh
systemctl enable xrdp
systemctl start ssh
systemctl start xrdp

# Setup challenges directory
CHAL_DIR="/home/user/challenges"
mkdir -p "$CHAL_DIR"

# Q2: Hidden file
echo "FLAG{ls_master}" > "$CHAL_DIR/.secret_flag"

# Q3: Hidden treasure somewhere in the filesystem
mkdir -p /var/hidden
echo "FLAG{treasure_found}" > /var/hidden/hidden_treasure.txt

# Q5: Compressed archives
echo "FLAG{zip_cracked}" > /tmp/flag1.txt
cd /tmp && zip "$CHAL_DIR/archive1.zip" flag1.txt && rm flag1.txt

echo "FLAG{tar_expert}" > /tmp/flag2.txt
cd /tmp && tar czf "$CHAL_DIR/archive2.tar.gz" flag2.txt && rm flag2.txt

# Q6: Executable file
cat > "$CHAL_DIR/run_me" << 'SCRIPT'
#!/bin/bash
echo "FLAG{chmod_pro}"
SCRIPT
chmod 644 "$CHAL_DIR/run_me"  # NOT executable yet — student must chmod +x

# Q7: File to delete
echo "Delete this file!" > "$CHAL_DIR/delete_me.txt"

# Q8: File with specific permissions
touch "$CHAL_DIR/permission_check"
chmod 640 "$CHAL_DIR/permission_check"

# Q9: File to edit
echo "Change this text" > "$CHAL_DIR/edit_me.txt"

# Q13: Download fastfetch .deb (or create a dummy)
ARCH=$(dpkg --print-architecture)
wget -q "https://github.com/fastfetch-cli/fastfetch/releases/latest/download/fastfetch-linux-${ARCH}.deb" \
    -O "$CHAL_DIR/fastfetch.deb" 2>/dev/null || \
    echo "# Download fastfetch manually" > "$CHAL_DIR/README_fastfetch.txt"

# Set ownership
chown -R user:user "$CHAL_DIR"
chown user:user /home/user/.bashrc

# Openbox autostart for GUI sessions
mkdir -p /home/user/.config/openbox
cat > /home/user/.config/openbox/autostart << 'EOF'
lxterminal &
pcmanfm &
EOF
chown -R user:user /home/user/.config

# Limit max processes per user (second layer defense against fork bombs)
cat >> /etc/security/limits.conf << 'LIMITS'
*    hard    nproc    150
*    soft    nproc    150
root hard    nproc    300
LIMITS

echo "=== Container initialized ==="
