#!/usr/bin/env bash
# Migration deploy VOLUME — Approche A (ordre 2026-06-14-1501) : MET À JOUR l'index DU
# volume existant (orientia-api-volume, déjà monté /app/data/embeddings) avec les NEUFS
# (52040 + fills + ROME). Le CORPUS reste dans l'image (deploy code+corpus léger).
#
# À LANCER PAR MATTEO via !  APRÈS que Claudette ait confirmé le snapshot rollback complet :
#   ! bash scripts/deploy_volume_1501.sh
#
# SÉQUENCE COMPLÈTE :
#   1) ce script : overwrite les 7 index du volume (l'app live tourne avec l'index EN
#      MÉMOIRE -> pas perturbée par l'écriture disque ; le neuf prend effet au deploy)
#   2) merge PR #162 (Dockerfile re-COPY corpus + .railwayignore + server.py fail-fast)
#   3) `! railway up --no-gitignore --ci`  (deploy code+corpus ~35M -> plus de 413)
#   4) Claudette vérifie /health=52040 + sonde fills/ROME, puis Jarvis cross-check avant LIVE
#
# ROLLBACK (la seule étape ~irréversible = l'overwrite) : re-upload le snapshot
#   /home/matteo_linux/orientia-volume-snapshot-20260614 sur le volume (mêmes 7 fichiers).
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
export PATH="$HOME/.nvm/versions/node/v22.22.1/bin:$PATH"
VOL=orientia-api-volume
SNAP=/home/matteo_linux/orientia-volume-snapshot-20260614
FILES=(formations.index formations_v7_formations.index formations_v7_metiers.index \
       formations_v7_statistiques.index formations_v7_aides_territoires.index \
       formations_partition_manifest.json golden_qa.index)

echo "=== GARDE-FOU rollback : le snapshot des 7 fichiers existe ? (sinon ABORT) ==="
for f in "${FILES[@]}"; do
  [ -s "$SNAP/$f" ] || { echo "  SNAPSHOT INCOMPLET ($f absent/vide) -> ABORT, pas d'overwrite sans rollback"; exit 3; }
done
echo "  OK snapshot complet ($(du -sh "$SNAP"|cut -f1)) -> rollback garanti"

echo "=== sanity : les 7 index NEUFS locaux (52040+fills, build 14:34) ==="
for f in "${FILES[@]}"; do
  [ -s "data/embeddings/$f" ] && echo "  OK data/embeddings/$f ($(du -h data/embeddings/$f|cut -f1))" \
    || { echo "  ABSENT data/embeddings/$f -> ABORT"; exit 2; }
done

echo "=== [1] RAILWAY_RUN_UID=0 (lecture volume garantie root, --skip-deploys) ==="
railway variables --set "RAILWAY_RUN_UID=0" --skip-deploys 2>&1 | tail -2

echo "=== [2] OVERWRITE les 7 index du volume avec les NEUFS ==="
echo "    (l'app 06-13 live tourne avec son index EN MÉMOIRE -> écriture disque sans impact ;"
echo "     le neuf est chargé au deploy code étape 3)"
for f in "${FILES[@]}"; do
  echo "-- upload $f --"
  railway volume files -v "$VOL" upload "data/embeddings/$f" "$f" --overwrite 2>&1 | tail -1
done

echo "=== [3] VÉRIF : le manifest du volume est bien le NEUF (attendu 52040, build 2026-06-14 14:34) ==="
railway volume files -v "$VOL" download formations_partition_manifest.json /tmp/vol_check_1501.json 2>&1 | tail -1
python3 -c "import json; m=json.load(open('/tmp/vol_check_1501.json')); print('  volume manifest:', m.get('total_fiches_in_source'), 'fiches, build', m.get('build_date'))"

echo "=== VOLUME_INDEX_UPDATED_DONE :: étape 2 = merge PR #162 + railway up --no-gitignore --ci. Claudette enchaîne les vérifs. ==="
