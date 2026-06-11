#!/usr/bin/env bash
# Mesure avant/apres garde-fou (RÈGLE 6 salaire + RÈGLE 7 reconversion) sur le
# subset combine (16q voie-d'acces C2a + 60q salaire). Instrument _FICHE_KEEP
# fixe = CONSTANT des 2 cotes. fact_card.py reste a HEAD (C2a) des 2 cotes.
# BEFORE = system.py @parent (sans garde-fou) ; AFTER = system.py @HEAD (garde-fou).
# Trap : restaure TOUJOURS system.py a HEAD, meme en cas d'echec.
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
source .venv/bin/activate
export PYTHONPATH=.

DIR=audit_empirique_2026-06-09
SUBSET=$DIR/subset_gardefou.json
RES=$DIR/results
PARENT=8d0bef7   # commit pre-garde-fou (parent de 1d2069b)

# Purge stale (run_battery/judge resume-safe skipperaient sinon)
rm -f $RES/gf_battery_before.json $RES/gf_battery_after.json \
      $RES/gf_ground_before.json $RES/gf_ground_after.json

restore() { git checkout HEAD -- src/prompt/system.py && echo "[trap] system.py restaure a HEAD"; }
trap restore EXIT

echo "=== BEFORE : system.py @parent (sans garde-fou) ==="
git checkout $PARENT -- src/prompt/system.py
python -c "from src.prompt.system import SYSTEM_PROMPT; print('  RÈGLE 6 present ?', 'RÈGLE 6' in SYSTEM_PROMPT)"
python $DIR/run_battery.py --eval-set $SUBSET --out $RES/gf_battery_before.json
echo "[ok] BEFORE battery"

echo "=== AFTER : system.py @HEAD (garde-fou) ==="
git checkout HEAD -- src/prompt/system.py
python -c "from src.prompt.system import SYSTEM_PROMPT; print('  RÈGLE 6 present ?', 'RÈGLE 6' in SYSTEM_PROMPT)"
python $DIR/run_battery.py --eval-set $SUBSET --out $RES/gf_battery_after.json
echo "[ok] AFTER battery"

echo "=== JUDGE before + after (Haiku temp=0, instrument fixe) ==="
python $DIR/judge_groundedness.py --in $RES/gf_battery_before.json --out $RES/gf_ground_before.json
python $DIR/judge_groundedness.py --in $RES/gf_battery_after.json  --out $RES/gf_ground_after.json
echo "=== GARDEFOU_MEASURE_DONE ==="
