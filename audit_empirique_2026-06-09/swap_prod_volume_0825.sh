#!/usr/bin/env bash
# Swap prod Railway volume + deploy (ordre 1535, option B). À LANCER PAR MATTEO via !
#   ! bash audit_empirique_2026-06-09/swap_prod_volume_0825.sh
# (les ops volume/deploy sont des mutations prod haute-sévérité : exécutées par
#  l'utilisateur en direct, pas par l'agent.)
#
# Aligne le volume sur l'état #2 : main index #2 (52040, dense-sigle-OFF) + quad
# sub-indexes alignés + manifest. Backups rollback déjà en local
# (data/embeddings/prod_rollback_v7_20260612/). golden_qa.index NON touché.
#
# ROLLBACK si un upload échoue : re-upload des 6 fichiers depuis prod_rollback_v7_20260612/
# + garder ORIENTIA_FICHES_PATH=data/processed/formations_v7.json + redeploy 5e0e4bf1.
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
export PATH="$HOME/.nvm/versions/node/v22.22.1/bin:$PATH"
VOL=orientia-api-volume
EMB=data/embeddings
FILES=(formations.index formations_v7_formations.index formations_v7_metiers.index formations_v7_statistiques.index formations_v7_aides_territoires.index formations_partition_manifest.json)

vol_total() { railway volume files -v "$VOL" list / --json 2>/dev/null | python3 -c "import sys,json;print(f\"{sum(f['size'] for f in json.load(sys.stdin).get('files',[]))/1e6:.1f} MB\")"; }

echo "=== [1] DELETE anciens fichiers volume ==="
for f in "${FILES[@]}"; do
  railway volume files -v "$VOL" delete "/$f" --yes >/dev/null 2>&1 && echo "  deleted $f" || echo "  (delete $f : absent ou échec, on continue)"
done
echo "  volume après delete : $(vol_total)"

echo "=== [2] UPLOAD nouveaux fichiers (index #2 + quad alignés + manifest) ==="
for f in "${FILES[@]}"; do
  if [ ! -f "$EMB/$f" ]; then echo "  ABSENT LOCAL: $EMB/$f -> ABORT"; exit 2; fi
  if railway volume files -v "$VOL" upload "$EMB/$f" "/$f" >/dev/null 2>&1; then
    echo "  uploaded $f ($(du -h "$EMB/$f" | cut -f1))"
  else
    echo "  !! UPLOAD FAIL $f -> STOP. ROLLBACK : re-upload depuis $EMB/prod_rollback_v7_20260612/ + env inchangé + redeploy 5e0e4bf1"; exit 3
  fi
done
echo "  volume après upload : $(vol_total)"

echo "=== [3] vérif listing volume ==="
railway volume files -v "$VOL" list / --json 2>/dev/null | python3 -c "import sys,json;[print(f\"  {x['name']}: {x['size']/1e6:.1f}MB\") for x in json.load(sys.stdin).get('files',[])]"

echo "=== [4] set ORIENTIA_FICHES_PATH=formations.json (sinon mode dégradé avec le nouveau Dockerfile) ==="
railway variables --set "ORIENTIA_FICHES_PATH=data/processed/formations.json" 2>&1 | tail -3

echo "=== [5] DEPLOY image alignée (corpus 52040) : railway up --no-gitignore ==="
railway up --no-gitignore --detach 2>&1 | tail -8

echo "=== SWAP_DEPLOY_DONE :: vérifier ensuite /health=52040 + sondes (Claudette enchaîne). ==="
