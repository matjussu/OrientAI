#!/usr/bin/env bash
# Migration deploy VOLUME (ordre 2026-06-14-1501) — étape 1/2 : créer + peupler le volume.
# À LANCER PAR MATTEO via !  (ops prod railway = intention utilisateur requise) :
#   ! bash scripts/deploy_volume_1501.sh
#
# Ce script NE déploie PAS le code. Il prépare le volume. Séquence complète :
#   1) ce script (volume add /app/data + upload des 9 artefacts NEUFS 52040+fills+ROME)
#   2) merge PR #162 (code volume-aware) sur main
#   3) railway up --no-gitignore --ci   (deploy code-only, lit l'index depuis le volume)
#   4) Claudette vérifie /health=52040 + sonde fills, puis Jarvis cross-check avant LIVE
#
# FENÊTRE DÉGRADÉE : monter le volume (vide) sur le service redéploie l'image 06-13 avec
# /app/data masqué -> 06-13 passe en mode dégradé (/health ok, /answer 503) le temps de
# l'upload + du deploy code (étape 3). Soft, borné, attendu (cf script Option C).
# ROLLBACK : `railway volume detach` (re-expose l'index baké 06-13) si besoin AVANT le switch.
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
export PATH="$HOME/.nvm/versions/node/v22.22.1/bin:$PATH"

echo "=== sanity : les 9 artefacts NEUFS sont présents (52040 + fills + ROME) ==="
ART=(
  data/processed/formations.json
  data/processed/golden_qa_meta.json
  data/embeddings/formations.index
  data/embeddings/formations_v7_formations.index
  data/embeddings/formations_v7_metiers.index
  data/embeddings/formations_v7_statistiques.index
  data/embeddings/formations_v7_aides_territoires.index
  data/embeddings/formations_partition_manifest.json
  data/embeddings/golden_qa.index
)
for f in "${ART[@]}"; do
  [ -f "$f" ] && echo "  OK $f ($(du -h "$f"|cut -f1))" || { echo "  ABSENT $f -> ABORT"; exit 2; }
done

echo "=== [0] volumes existants (pour info / éviter doublon) ==="
railway volume list 2>&1 | tail -10

echo "=== [1] CRÉE + MONTE le volume à /app/data (mount OBLIGATOIRE = /app/data pour aligner le manifest) ==="
echo "    (déclenche un redeploy 06-13 avec volume vide -> fenêtre dégradée jusqu'au deploy code)"
railway volume add --mount-path /app/data 2>&1 | tail -10

echo "=== [1.5] RAILWAY_RUN_UID=0 (root) — GARANTIT la LECTURE des fichiers volume (owned root) ==="
echo "    (image sans directive USER = root, mais on force RAILWAY_RUN_UID=0 pour éliminer"
echo "     tout risque de permission-denied non-root sur le volume -> fail-fast persistant)"
echo "    --skip-deploys : prend effet au deploy code (étape 3), n'impacte pas 06-13 maintenant"
railway variables --set "RAILWAY_RUN_UID=0" --skip-deploys 2>&1 | tail -3

echo "=== [2] UPLOAD des 9 artefacts NEUFS vers le volume ==="
railway volume files upload data/processed/formations.json        /app/data/processed/formations.json        --overwrite 2>&1 | tail -2
railway volume files upload data/processed/golden_qa_meta.json     /app/data/processed/golden_qa_meta.json     --overwrite 2>&1 | tail -2
railway volume files upload data/embeddings/formations.index       /app/data/embeddings/formations.index       --overwrite 2>&1 | tail -2
railway volume files upload data/embeddings/formations_v7_formations.index      /app/data/embeddings/formations_v7_formations.index      --overwrite 2>&1 | tail -2
railway volume files upload data/embeddings/formations_v7_metiers.index         /app/data/embeddings/formations_v7_metiers.index         --overwrite 2>&1 | tail -2
railway volume files upload data/embeddings/formations_v7_statistiques.index    /app/data/embeddings/formations_v7_statistiques.index    --overwrite 2>&1 | tail -2
railway volume files upload data/embeddings/formations_v7_aides_territoires.index /app/data/embeddings/formations_v7_aides_territoires.index --overwrite 2>&1 | tail -2
railway volume files upload data/embeddings/formations_partition_manifest.json  /app/data/embeddings/formations_partition_manifest.json  --overwrite 2>&1 | tail -2
railway volume files upload data/embeddings/golden_qa.index        /app/data/embeddings/golden_qa.index        --overwrite 2>&1 | tail -2

echo "=== [3] VÉRIF : les fichiers sont bien aux bons chemins ==="
echo "--- /app/data/embeddings (attendu : 7 fichiers) ---"
railway volume files list /app/data/embeddings 2>&1 | tail -12
echo "--- /app/data/processed (attendu : formations.json + golden_qa_meta.json) ---"
railway volume files list /app/data/processed 2>&1 | tail -6

echo "=== VOLUME_PEUPLE_DONE :: étape 2 = merge PR #162 + railway up --no-gitignore --ci. Claudette enchaîne les vérifs. ==="
