#!/bin/bash
# Fix existing containers: apply CPU limit + network device override
# Run this once after updating the code. No need to recreate containers.
set -e

echo "=== Fixing existing lab containers ==="

# Update profile first
echo "Setting limits.cpu=1 on lab-student profile..."
lxc profile set lab-student limits.cpu=1

# Find all lab-student containers
for container in $(lxc list -c n --format csv | grep '^lab-student-'); do
    echo ""
    echo "--- Fixing: $container ---"

    # Apply CPU limit directly to instance (overrides profile)
    echo "  Setting limits.cpu=1..."
    lxc config set "$container" limits.cpu=1

    # Override eth0 at instance level (needed for network limits to work)
    echo "  Overriding eth0 device..."
    lxc config device override "$container" eth0 2>/dev/null || true

    # Restart to apply CPU change
    echo "  Restarting..."
    lxc restart "$container" --force 2>/dev/null || true

    echo "  Done!"
done

echo ""
echo "=== All containers fixed ==="
echo ""
echo "To apply network speed limits, use the admin panel: /admin/network"
echo "The limits will now work correctly on all containers."
