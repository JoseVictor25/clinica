#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ ! -f .env.ec2 ]]; then
  echo "Falta .env.ec2. Copia .env.ec2.example y completa los valores reales."
  exit 1
fi

EC2_ENV_FILE=.env.ec2 docker compose --env-file .env.ec2 -f compose.ec2.yaml config --quiet
EC2_ENV_FILE=.env.ec2 docker compose --env-file .env.ec2 -f compose.ec2.yaml build --pull
EC2_ENV_FILE=.env.ec2 docker compose --env-file .env.ec2 -f compose.ec2.yaml up -d --remove-orphans
EC2_ENV_FILE=.env.ec2 docker compose --env-file .env.ec2 -f compose.ec2.yaml ps
