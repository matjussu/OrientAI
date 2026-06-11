#!/usr/bin/env bash
# Gate Option B (J2 U1) — A/B temp=0 sur les 48 questions SELECT-eligibles.
# BEFORE = pipeline.py @pre-Option-B (bypass SELECT -> refus aveugle).
# AFTER  = pipeline.py @HEAD (fall-through vers le RAG gardé).
# Pool filter (structured_select) + run_battery (instrument _FICHE_KEEP + tag
# fallthrough) CONSTANTS des 2 cotes. Generation temp=0 deterministe.
# Gate (Jarvis cond. 3) : honest_refusal en baisse ET hallucinated_numbers +
# metric_substitution NE montent PAS. Sinon -> revert le fall-through.
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
source .venv/bin/activate
export PYTHONPATH=.
DIR=audit_empirique_2026-06-09
SUBSET=$DIR/subset_select48.json
RES=$DIR/results
PRE_OPTB=8d1e0cd   # commit pool filter, pipeline.py = ancien bypass (parent de 8c9a9fc)
rm -f $RES/ob_battery_before.json $RES/ob_battery_after.json \
      $RES/ob_ground_before.json $RES/ob_ground_after.json
restore() { git checkout HEAD -- src/rag/pipeline.py && echo "[trap] pipeline.py restaure HEAD"; }
trap restore EXIT
echo "=== BEFORE temp=0 : pipeline.py @pre-Option-B (bypass -> refus) ==="
git checkout $PRE_OPTB -- src/rag/pipeline.py
python -c "import inspect, src.rag.pipeline as p; print('  Option B present ?', 'last_select_fallthrough' in inspect.getsource(p))"
python $DIR/run_battery.py --eval-set $SUBSET --out $RES/ob_battery_before.json --temperature 0
echo "=== AFTER temp=0 : pipeline.py @HEAD (Option B fall-through RAG) ==="
git checkout HEAD -- src/rag/pipeline.py
python -c "import inspect, src.rag.pipeline as p; print('  Option B present ?', 'last_select_fallthrough' in inspect.getsource(p))"
python $DIR/run_battery.py --eval-set $SUBSET --out $RES/ob_battery_after.json --temperature 0
echo "=== JUDGE (Haiku temp=0) ==="
python $DIR/judge_groundedness.py --in $RES/ob_battery_before.json --out $RES/ob_ground_before.json
python $DIR/judge_groundedness.py --in $RES/ob_battery_after.json  --out $RES/ob_ground_after.json
echo "=== OPTIONB_DONE ==="
