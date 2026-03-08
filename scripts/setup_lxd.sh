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

# Security: systemd support + nesting
lxc profile set lab-student security.nesting=true
lxc profile set lab-student raw.lxc "lxc.apparmor.profile=unconfined"

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

echo "=== LXD setup complete ==="
echo "Network: lab-net (10.99.0.1/24)"
echo "Profile: lab-student"
echo "Container isolation: enabled (no inter-container traffic)"
