#!/usr/bin/env bash
# Deploy Option C (ordre 1535) — index+quads dans l'image, volume abandonné.
# À LANCER PAR MATTEO via !  (ops prod : détach volume + deploy = mutations gatées) :
#   ! bash audit_empirique_2026-06-09/deploy_option_c_0825.sh
#
# Séquence DETACH-FIRST (fenêtre dégradée VISIBLE pendant le build, vs up-first =
# désaligné silencieux corpus-52040/index-47220 à cause du shadow-mount du volume).
# Doit tourner depuis la branche feature/orientai-prod-option-c (Dockerfile option C).
#
# ROLLBACK si besoin : railway volume attach -v orientia-api-volume (re-monte le volume
# v7 conservé) + railway variables --set ORIENTIA_FICHES_PATH=data/processed/formations_v7.json
# + redeploy de l'image 5e0e4bf1.
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
export PATH="$HOME/.nvm/versions/node/v22.22.1/bin:$PATH"

echo "=== branche courante (doit être feature/orientai-prod-option-c) ===" && git branch --show-current
echo "=== sanity : artefacts présents dans le contexte de build ==="
for f in data/embeddings/formations.index data/embeddings/formations_v7_formations.index data/embeddings/formations_partition_manifest.json data/processed/formations.json; do
  [ -f "$f" ] && echo "  OK $f ($(du -h "$f"|cut -f1))" || { echo "  ABSENT $f -> ABORT"; exit 2; }
done

echo "=== [1] set ORIENTIA_FICHES_PATH=formations.json (sans deploy) ==="
railway variables --set "ORIENTIA_FICHES_PATH=data/processed/formations.json" --skip-deploys 2>&1 | tail -3

echo "=== [2] DETACH volume (data conservée = filet rollback ; old image -> dégradé visible le temps du build) ==="
railway volume detach -v orientia-api-volume -y 2>&1 | tail -5

echo "=== [3] BUILD + DEPLOY image Option C (corpus+index+quads bakés, sans volume -> aligné) ==="
echo "    (si échec sur la taille du tarball -> fallback option D, prévenir Claudette)"
railway up --no-gitignore --ci 2>&1 | tail -40

echo "=== DEPLOY_OPTION_C_DONE :: Claudette enchaîne les vérifs URL publique. ==="
