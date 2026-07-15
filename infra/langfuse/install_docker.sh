#!/usr/bin/env bash
# Install Docker Engine + Compose v2 on Ubuntu 24.04 (noble) — WSL2 compatible.
# Source: https://docs.docker.com/engine/install/ubuntu/
# Run once with: sudo bash infra/langfuse/install_docker.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Ce script doit être lancé avec sudo." >&2
  exit 1
fi

echo "[1/6] apt-get update + prérequis"
apt-get update -y
apt-get install -y ca-certificates curl gnupg

echo "[2/6] Ajout de la clé GPG Docker officielle"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo "[3/6] Ajout du repo Docker à apt sources"
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -y

echo "[4/6] Installation Docker Engine + Compose v2"
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "[5/6] Ajout de l'utilisateur au groupe docker (évite sudo)"
USERNAME=${SUDO_USER:-matteo_linux}
usermod -aG docker "$USERNAME"

echo "[6/6] Activation du service Docker (systemd actif sous WSL2)"
systemctl enable docker
systemctl start docker

echo ""
echo "✅ Docker installé."
docker --version
docker compose version
echo ""
echo "⚠️  Important : la nouvelle appartenance au groupe 'docker' ne s'applique"
echo "qu'après reconnexion shell. Pour la session courante, lance :"
echo "    newgrp docker"
echo "ou ouvre un nouveau terminal WSL."
