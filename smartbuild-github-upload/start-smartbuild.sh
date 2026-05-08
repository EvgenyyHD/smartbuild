#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose up --build -d

echo "SmartBuild is running."
echo "Open: http://localhost:${HTTP_PORT:-80}"
