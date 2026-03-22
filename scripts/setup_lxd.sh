#!/bin/bash
# Setup LXD network and profile for isolated student containers
set -e

echo "=== Setting up LXD for Linux Lab ==="

# Create isolated network (students can't ping each other)
lxc network create lab-net \
    ipv4.address=10.99.0.1/24 \
    ipv4.nat=true \
    ipv6.address=none \
    dns.domain=lab.local

# Create profile
lxc profile create lab-student 2>/dev/null || true
lxc profile device add lab-student eth0 nic \
    network=lab-net \
    name=eth0 2>/dev/null || true
lxc profile device add lab-student root disk \
    pool=default \
    path=/ \
    size=5GB 2>/dev/null || true

# Resource limits: single CPU core per container
lxc profile set lab-student limits.cpu=1
lxc profile set lab-student limits.processes=256

# Security: systemd support + nesting (required for systemd in container)
lxc profile set lab-student security.nesting=true
# Use default AppArmor — do NOT set unconfined (prevents host access)
# Explicitly set unprivileged to prevent host UID mapping
lxc profile set lab-student security.privileged=false

# Apply ebtables rules to prevent inter-container traffic
# Each container only talks to host (10.99.0.1)
cat > /tmp/lab-net-isolate.sh << 'EOF'
#!/bin/bash
# Drop traffic between containers on lab-net
# Only allow container <-> host gateway
ebtables -A FORWARD -i lxdbr-lab-net -o lxdbr-lab-net -j DROP 2>/dev/null || \
iptables -I FORWARD -i lab-net -o lab-net -j DROP
EOF
chmod +x /tmp/lab-net-isolate.sh
bash /tmp/lab-net-isolate.sh

# ─── Block container → host access ──────────────────────────────────────
# Create a dedicated chain for lab-net → host filtering
iptables -N LAB_HOST_FILTER 2>/dev/null || iptables -F LAB_HOST_FILTER

# Allow DNS (container needs to resolve via gateway for NAT internet)
iptables -A LAB_HOST_FILTER -p udp --dport 53 -j ACCEPT
iptables -A LAB_HOST_FILTER -p tcp --dport 53 -j ACCEPT

# Allow DHCP
iptables -A LAB_HOST_FILTER -p udp --dport 67 -j ACCEPT

# Drop everything else from containers to the host gateway IP
iptables -A LAB_HOST_FILTER -j DROP

# Hook it into INPUT: traffic from lab-net destined to host
iptables -C INPUT -i lxdbr0 -d 10.99.0.1 -j LAB_HOST_FILTER 2>/dev/null || \
    iptables -I INPUT -i lxdbr0 -d 10.99.0.1 -j LAB_HOST_FILTER
# Also cover the lab-net bridge name variant
iptables -C INPUT -i lab-net -d 10.99.0.1 -j LAB_HOST_FILTER 2>/dev/null || \
    iptables -I INPUT -i lab-net -d 10.99.0.1 -j LAB_HOST_FILTER

# Allow DHCP broadcasts (255.255.255.255) — must come before the catch-all DROP
iptables -C INPUT -i lxdbr0 -d 255.255.255.255 -p udp --dport 67 -j ACCEPT 2>/dev/null || \
    iptables -I INPUT -i lxdbr0 -d 255.255.255.255 -p udp --dport 67 -j ACCEPT
iptables -C INPUT -i lab-net -d 255.255.255.255 -p udp --dport 67 -j ACCEPT 2>/dev/null || \
    iptables -I INPUT -i lab-net -d 255.255.255.255 -p udp --dport 67 -j ACCEPT

# Block containers from reaching host on ANY host IP (not just 10.99.0.1)
# This prevents access via host's public IP, 127.0.0.1, etc.
# But allow FORWARD (NAT internet + guacd) — only block INPUT to host itself
iptables -C INPUT -i lxdbr0 ! -d 10.99.0.0/24 -j DROP 2>/dev/null || \
    iptables -A INPUT -i lxdbr0 ! -d 10.99.0.0/24 -j DROP
iptables -C INPUT -i lab-net ! -d 10.99.0.0/24 -j DROP 2>/dev/null || \
    iptables -A INPUT -i lab-net ! -d 10.99.0.0/24 -j DROP

# Block access to common host-local services via FORWARD too
# (metadata service, cloud-init, etc.)
iptables -C FORWARD -s 10.99.0.0/24 -d 169.254.169.254 -j DROP 2>/dev/null || \
    iptables -I FORWARD -s 10.99.0.0/24 -d 169.254.169.254 -j DROP

echo "=== LXD setup complete ==="
echo "Network: lab-net (10.99.0.1/24)"
echo "Profile: lab-student"
echo "Container isolation: enabled (no inter-container traffic)"
echo "Host protection: enabled (containers cannot reach host services)"
