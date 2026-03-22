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
    unzip xz-utils file man-db dnsutils \
    pcmanfm lxterminal openbox xrdp xorgxrdp dbus-x11 \
    locales

# Generate locale
sed -i 's/# zh_TW.UTF-8/zh_TW.UTF-8/' /etc/locale.gen
locale-gen

# Create student user
if ! id "user" &>/dev/null; then
    useradd -m -s /bin/bash user
    echo "user:user" | chpasswd
    usermod -aG sudo user
fi

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

# DNS challenge: use dnsmasq to override foo.com → 0.0.0.0
# Students must learn to query a specific DNS server (dig @1.1.1.1)
#apt-get install -y --no-install-recommends dnsmasq

# Point resolv.conf to local dnsmasq
echo "nameserver 127.0.0.53" > /etc/resolv.conf

# Override foo.com with incorrect IP
echo "123.123.123.123 foo.com" >> /etc/hosts

#systemctl enable dnsmasq
#systemctl restart dnsmasq

# Setup challenges directory
CHAL_DIR="/home/user/challenges"
mkdir -p "$CHAL_DIR"
mkdir -p /home/user/documents

# ============================================================
# Challenge file setup (matches challenges.json question order)
# ============================================================

# Q6: Hidden file (ls -a)
echo "FLAG{ls_master}" > "$CHAL_DIR/.secret_flag"

# Q8: File to edit
echo "Change this text" > "$CHAL_DIR/edit_me.txt"

# Q9: mkdir target (students need to create this)
# (intentionally NOT created — they must mkdir it)

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

# Q13: Hidden treasure somewhere in the filesystem
mkdir -p /var/lib
echo "FLAG{treasure_found}" > /var/lib/hidden_treasure.txt

# Q14: Symlink target (original.txt already created in Q11)

# Q18: Compress and extract challenges
mkdir -p "$CHAL_DIR/compress_me"
echo "file to compress 1" > "$CHAL_DIR/compress_me/data1.txt"
echo "file to compress 2" > "$CHAL_DIR/compress_me/data2.txt"

# Create a tar.gz for students to extract
mkdir -p /tmp/extract_content
echo "extracted file 1" > /tmp/extract_content/extracted1.txt
echo "extracted file 2" > /tmp/extract_content/extracted2.txt
(cd /tmp && tar czf "$CHAL_DIR/extract_me.tar.gz" extract_content/)
rm -rf /tmp/extract_content

# Q19-21: Script file (owned by root, not executable)
cat > "$CHAL_DIR/22.sh" << 'SCRIPT'
#!/bin/bash
echo "This is GDG NTUST."
SCRIPT
chmod 644 "$CHAL_DIR/22.sh"
chown root:root "$CHAL_DIR/22.sh"

# Set ownership for challenges (except protected_dir and 22.sh which are root-owned)
chown user:user "$CHAL_DIR"
chown user:user "$CHAL_DIR/.secret_flag"
chown user:user "$CHAL_DIR/edit_me.txt"
chown user:user "$CHAL_DIR/delete_me.txt"
chown -R user:user "$CHAL_DIR/remove_this_dir"
# protected_dir stays root-owned (Q10)
chown user:user "$CHAL_DIR/original.txt"
chown -R user:user "$CHAL_DIR/sample_dir"
chown user:user "$CHAL_DIR/move_me.txt"
chown user:user "$CHAL_DIR/rename_me.txt"
chown -R user:user "$CHAL_DIR/moved"
chown -R user:user "$CHAL_DIR/compress_me"
chown user:user "$CHAL_DIR/extract_me.tar.gz"
# 22.sh stays root-owned (Q19-20)

chown user:user /home/user/.bashrc
chown -R user:user /home/user/documents

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

# ─── Security hardening (prevent container→host jailbreak) ──────────────

# 1. Block the host gateway IP from inside the container (defense in depth)
#    Primary protection is at host iptables level, this is a backup
cat > /etc/network/if-up.d/block-host << 'BLOCKHOST'
#!/bin/sh
# Prevent user from accessing the LXD host gateway
iptables -C OUTPUT -d 10.99.0.1 -p tcp --dport 22 -j DROP 2>/dev/null || \
    iptables -A OUTPUT -d 10.99.0.1 -p tcp --dport 22 -j DROP
iptables -C OUTPUT -d 10.99.0.1 -p tcp --dport 8080 -j DROP 2>/dev/null || \
    iptables -A OUTPUT -d 10.99.0.1 -p tcp --dport 8080 -j DROP
iptables -C OUTPUT -d 10.99.0.1 -p tcp --dport 5000 -j DROP 2>/dev/null || \
    iptables -A OUTPUT -d 10.99.0.1 -p tcp --dport 5000 -j DROP
BLOCKHOST
chmod +x /etc/network/if-up.d/block-host

# 2. Disable kernel module loading from inside container
echo "install * /bin/false" > /etc/modprobe.d/disable-modules.conf 2>/dev/null || true

# 3. Restrict dmesg access (hide kernel messages from unprivileged users)
echo "kernel.dmesg_restrict=1" >> /etc/sysctl.conf
sysctl -w kernel.dmesg_restrict=1 2>/dev/null || true

# 4. Hide other users' processes
echo "proc /proc proc defaults,hidepid=2 0 0" >> /etc/fstab 2>/dev/null || true

# 5. Remove tools that could aid container escape
apt-get remove -y --purge strace ltrace 2>/dev/null || true
# Prevent installing debug/escape tools
cat > /etc/apt/preferences.d/block-debug << 'APTPREF'
Package: strace ltrace gdb
Pin: release *
Pin-Priority: -1
APTPREF

echo "=== Container initialized ==="
