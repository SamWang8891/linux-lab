#!/bin/bash
# Generate Guacamole DB init SQL and start services
set -e

cd "$(dirname "$0")/.."

# Load .env if exists
if [ -f .env ]; then
    echo "=== Loading .env ==="
    export $(grep -v '^#' .env | xargs)
fi

echo "=== Cleaning up old Guacamole containers and volumes ==="
docker compose -f docker-compose.guac.yml down -v 2>/dev/null || true

echo "=== Generating Guacamole DB schema ==="
docker run --rm guacamole/guacamole /opt/guacamole/bin/initdb.sh --postgresql \
    > scripts/guac-initdb.sql

echo "=== Starting Guacamole stack ==="
docker compose -f docker-compose.guac.yml up -d

echo "=== Waiting for Guacamole to be ready ==="
for i in $(seq 1 60); do
    if curl -sf http://localhost:8080/guacamole/ > /dev/null 2>&1; then
        echo ""
        echo "Guacamole is ready!"
        echo "URL: http://localhost:8080/guacamole/"
        echo "Default login: guacadmin / guacadmin"

        # Change default admin password if GUAC_ADMIN_PASS is set
        if [ -n "$GUAC_ADMIN_PASS" ] && [ "$GUAC_ADMIN_PASS" != "guacadmin" ]; then
            echo ""
            echo "=== Changing guacadmin password ==="
            TOKEN=$(curl -sf -X POST 'http://localhost:8080/guacamole/api/tokens' \
                -d 'username=guacadmin&password=guacadmin' | python3 -c "import sys,json; print(json.load(sys.stdin)['authToken'])" 2>/dev/null)
            if [ -n "$TOKEN" ]; then
                curl -sf -X PUT "http://localhost:8080/guacamole/api/session/data/postgresql/users/guacadmin/password?token=$TOKEN" \
                    -H 'Content-Type: application/json' \
                    -d "{\"oldPassword\":\"guacadmin\",\"newPassword\":\"$GUAC_ADMIN_PASS\"}" && \
                    echo "guacadmin password changed to value from .env" || \
                    echo "Warning: Failed to change guacadmin password"
            fi
        fi
        exit 0
    fi
    printf "."
    sleep 2
done
echo ""
echo "Guacamole did not start in time. Check: docker compose -f docker-compose.guac.yml logs"
exit 1
