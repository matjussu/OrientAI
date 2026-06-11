#!/usr/bin/env bash
# A/B garde-fou en generation DETERMINISTE (temperature=0) sur 15 questions
# salaire base. Objectif : isoler l'effet du garde-fou du bruit de generation
# (le run temp=0.3 etait noise-dominated). Toute difference before/after est
# alors ATTRIBUABLE au garde-fou (seul system.py change). Instrument _FICHE_KEEP
# fixe + fact_card@HEAD constants. Judge Haiku temp=0 (deja deterministe).
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
source .venv/bin/activate
export PYTHONPATH=.
DIR=audit_empirique_2026-06-09
SUBSET=$DIR/subset_salaire_base.json
RES=$DIR/results
PARENT=8d0bef7
rm -f $RES/gf0_battery_before.json $RES/gf0_battery_after.json \
      $RES/gf0_ground_before.json $RES/gf0_ground_after.json
restore() { git checkout HEAD -- src/prompt/system.py && echo "[trap] system.py restaure HEAD"; }
trap restore EXIT
echo "=== BEFORE temp=0 : system.py @parent (sans garde-fou) ==="
git checkout $PARENT -- src/prompt/system.py
python $DIR/run_battery.py --eval-set $SUBSET --out $RES/gf0_battery_before.json --temperature 0
echo "=== AFTER temp=0 : system.py @HEAD (garde-fou) ==="
git checkout HEAD -- src/prompt/system.py
python $DIR/run_battery.py --eval-set $SUBSET --out $RES/gf0_battery_after.json --temperature 0
echo "=== JUDGE (Haiku temp=0) ==="
python $DIR/judge_groundedness.py --in $RES/gf0_battery_before.json --out $RES/gf0_ground_before.json
python $DIR/judge_groundedness.py --in $RES/gf0_battery_after.json  --out $RES/gf0_ground_after.json
echo "=== GF0_DONE ==="
