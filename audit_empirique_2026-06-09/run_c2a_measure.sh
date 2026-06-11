#!/usr/bin/env bash
# Mesure avant/après C2a sur le sous-ensemble reconversion (28q).
# BEFORE = fact_card.py au parent 634189e (sans dispositifs_reconversion)
# AFTER  = fact_card.py à HEAD (avec C2a). run_battery.py garde le fix instrument (committé).
# Trap : restaure TOUJOURS fact_card.py à HEAD, même en cas d'échec.
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
source .venv/bin/activate
export PYTHONPATH=.

DIR=audit_empirique_2026-06-09
SUBSET=$DIR/subset_C2a_reconversion.json
RES=$DIR/results

restore() { git checkout HEAD -- src/rag/fact_card.py && echo "[trap] fact_card.py restauré à HEAD"; }
trap restore EXIT

echo "=== BEFORE : revert fact_card.py au parent (sans C2a) ==="
git checkout 634189e -- src/rag/fact_card.py
python -c "from src.rag.fact_card import FactCard; print('  dispositifs_reconversion présent ?', 'dispositifs_reconversion' in FactCard.__dataclass_fields__)"
python $DIR/run_battery.py --eval-set $SUBSET --out $RES/c2a_battery_before.json
echo "[ok] BEFORE battery écrit"

echo "=== AFTER : restaure fact_card.py à HEAD (avec C2a) ==="
git checkout HEAD -- src/rag/fact_card.py
python -c "from src.rag.fact_card import FactCard; print('  dispositifs_reconversion présent ?', 'dispositifs_reconversion' in FactCard.__dataclass_fields__)"
python $DIR/run_battery.py --eval-set $SUBSET --out $RES/c2a_battery_after.json
echo "[ok] AFTER battery écrit"

echo "=== JUDGE before + after (Haiku, temp=0) ==="
python $DIR/judge_groundedness.py --in $RES/c2a_battery_before.json --out $RES/c2a_ground_before.json
python $DIR/judge_groundedness.py --in $RES/c2a_battery_after.json  --out $RES/c2a_ground_after.json
echo "=== C2A_MEASURE_DONE ==="
