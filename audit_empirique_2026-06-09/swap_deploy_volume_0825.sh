#!/usr/bin/env bash
# Swap volume + deploy (ordre 1535, approche volume après agrandissement du volume).
# PRÉREQUIS : (1) restore_prod_safe déjà passé (prod saine sur 47220, volume attaché,
# env v7) ; (2) volume Railway AGRANDI (>500MB) pour avoir la place d'uploader l'index #2.
# À LANCER PAR MATTEO via !  (mutations prod) :
#   ! bash audit_empirique_2026-06-09/swap_deploy_volume_0825.sh
#
# Aligne le volume sur l'état #2 (52040, dense-sigle-OFF) puis déploie l'image
# corpus-52040 (branche feature/orientai-prod-revert-c-volume). Une seule transition :
# l'ancienne image sert pendant le build, la nouvelle arrive alignée (index volume + corpus image).
# ROLLBACK si échec : restore_prod_safe_0825.sh (re-attach + env v7 + redeploy 5e0e4bf1).
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
export PATH="$HOME/.nvm/versions/node/v22.22.1/bin:$PATH"
VOL=orientia-api-volume
EMB=data/embeddings
FILES=(formations.index formations_v7_formations.index formations_v7_metiers.index formations_v7_statistiques.index formations_v7_aides_territoires.index formations_partition_manifest.json)

echo "=== branche (doit être feature/orientai-prod-revert-c-volume : corpus-seul image) ===" && git branch --show-current

echo "=== [0] capacité volume (doit être > ~650MB pour la place) ==="
railway volume list 2>&1 | tail -6 || true

echo "=== [1] UPLOAD index #2 + quads + manifest sur le volume (place dispo après upgrade) ==="
for f in "${FILES[@]}"; do
  [ -f "$EMB/$f" ] || { echo "  ABSENT LOCAL $EMB/$f -> ABORT"; exit 2; }
  echo "  -- $f ($(du -h "$EMB/$f"|cut -f1)) : delete best-effort puis upload --"
  railway volume files -v "$VOL" delete "/$f" --yes 2>&1 | tail -1 || echo "    (delete a échoué/absent, on tente l'upload en overwrite)"
  if railway volume files -v "$VOL" upload "$EMB/$f" "/$f" 2>&1 | tail -2; then
    echo "    uploaded $f"
  else
    echo "    !! UPLOAD FAIL $f -> STOP. Rollback : restore_prod_safe_0825.sh"; exit 3
  fi
done

echo "=== [2] listing volume après upload ==="
railway volume files -v "$VOL" list / 2>&1 | tail -10

echo "=== [3] set ORIENTIA_FICHES_PATH=formations.json (sans deploy ; l'image #2 l'a) ==="
railway variables --set "ORIENTIA_FICHES_PATH=data/processed/formations.json" --skip-deploys 2>&1 | tail -2

echo "=== [4] BUILD + DEPLOY image corpus-52040 (petit tarball ; index lu depuis le volume) ==="
railway up --no-gitignore --ci 2>&1 | tail -30

echo "=== SWAP_DEPLOY_VOLUME_DONE :: Claudette enchaîne les vérifs URL publique. ==="
