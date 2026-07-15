#!/usr/bin/env bash
# RESTAURATION état sûr prod (ordre 1535) — Option C a échoué (tarball 1.8GB > limite
# Cloudflare 413). Le volume a été détaché + ORIENTIA_FICHES_PATH=formations.json posé,
# ce qui rend la prod FRAGILE (saine en mémoire mais casserait au moindre restart).
# Ce script restaure l'état d'origine (volume ré-attaché + env v7) -> prod
# restart-survivable sur l'ancien index 47220, le temps de préparer l'option D.
# À LANCER PAR MATTEO via !  (mutations prod) :
#   ! bash audit_empirique_2026-06-09/restore_prod_safe_0825.sh
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
export PATH="$HOME/.nvm/versions/node/v22.22.1/bin:$PATH"

echo "=== [1] RE-ATTACH volume (index 47220 redevient dispo au restart) ==="
railway volume attach -v orientia-api-volume -y 2>&1 | tail -4

echo "=== [2] REVERT ORIENTIA_FICHES_PATH -> formations_v7.json (match l'ancienne image) ==="
railway variables --set "ORIENTIA_FICHES_PATH=data/processed/formations_v7.json" 2>&1 | tail -3

echo "=== [3] attendre la stabilisation puis /health ==="
sleep 25
curl -s --max-time 20 https://orientia-api-production.up.railway.app/health 2>&1 | head -c 300
echo ""
echo "=== RESTORE_DONE :: prod doit être Online sur index_size 47220 (état d'origine sûr). ==="
