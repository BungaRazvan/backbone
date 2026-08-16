#!/bin/bash
set -e

cd /home/pi/projects/backbone

echo "Stopping BMW bridge and listener services..."
docker compose stop bmw-bridge bmw-listener

echo "Removing bridge containers..."
docker compose rm -f bmw-bridge bmw-listener

# Option 1: Just take it down so you can run your local dev version without token conflicts
if [ "$1" == "--down" ]; then
    echo "Bridge and listener stopped for local dev."
    exit 0
fi

# Option 2: Wipe ONLY the expired tokens (preserving .env), re-auth, and restart services
if [ "$1" == "--reauth" ]; then
    echo "Wiping old session tokens while preserving your .env file..."
    docker compose run --rm --entrypoint sh bmw-bridge -c "rm -rf /app/state/bmw-mqtt-bridge/tokens*"
    
    echo "Starting interactive authentication..."
    docker compose run --rm -it bmw-bridge ./bmw_flow.sh
fi

echo "Starting bridge and listener services..."
docker compose up -d bmw-bridge bmw-listener
echo "Done."