#!/usr/bin/env bash
# Run this once to generate secrets for your .env
set -euo pipefail

echo "# ── Generated secrets ──────────────────────────────────────"
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)"
echo "REDIS_PASSWORD=$(openssl rand -hex 16)"
echo "FLOWER_PASSWORD=$(openssl rand -hex 12)"
echo ""
echo "# Fernet key (copy exactly, including the trailing =)"
python3 -c "from cryptography.fernet import Fernet; print('FERNET_KEY=' + Fernet.generate_key().decode())"
