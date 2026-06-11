#!/usr/bin/env bash
# Run gel 497q (J3 étape 6, GO Matteo 2026-06-11 14h53) — produit les chiffres du gel
# VivaTech + la VRAIE mesure F1. HEAD complet : rubrique figée + R8 + F1 + géo NARROW.
# Resume-safe (run_battery + judge skippent les ids déjà faits). 1 passe propre,
# lecture par-question (le harnais est non-déterministe run-to-run à temp=0).
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
export PYTHONPATH=.
PY=.venv/bin/python
DIR=audit_empirique_2026-06-09
RES=$DIR/results
EVAL=$DIR/eval_set_full.json

# 0. backup baseline figée (sécurité — le run n'overwrite PAS la baseline, écrit en gel_*,
#    mais Matteo/Jarvis ont demandé un backup avant tout, on l'assure).
BK=$DIR/baseline_bak_pre_gel
mkdir -p "$BK" && cp $DIR/baseline/*.json "$BK"/ 2>/dev/null && echo "[backup] baseline -> $BK"

echo "=== [1/3] GÉNÉRATION 497q HEAD (R8+F1+géo NARROW, temp=0) ==="
$PY $DIR/run_battery.py --eval-set $EVAL --out $RES/gel_battery.json --temperature 0
echo "=== GEN_DONE ==="

echo "=== [2/3] JUGEMENT 497q (rubrique figée answered_alternative_disclaimed) ==="
$PY $DIR/judge_groundedness.py --in $RES/gel_battery.json --out $RES/gel_ground.json
echo "=== JUDGE_DONE ==="

echo "=== [3/3] RE-JUGEMENT baseline figée (MÊME nouvelle rubrique, judge-only) ==="
$PY $DIR/judge_groundedness.py --in $DIR/baseline/baseline_full_battery.json --out $RES/baseline_rejudge_newrubric.json
echo "=== REJUDGE_DONE ==="
echo "=== GEL_497Q_DONE ==="
