#!/usr/bin/env bash
# CI minimale golden 50q (Phase 4, order 0825). À lancer pendant/après un re-embed.
#   [1] BLOQUANT  : recall retrieval (déterministe, hors juge, <5 min). exit!=0 = gate rouge.
#   [2] NON BLOQUANT : génération + groundedness sur les 50q, moyenne imprimée en alerte.
# Le step 2 appelle Mistral (gen) + Haiku (juge) -> plus lent/coûteux, d'où séparé et
# jamais bloquant. Le gate de non-régression est le step 1.
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
source .venv/bin/activate
export PYTHONPATH=.
DIR=audit_empirique_2026-06-09
RES=$DIR/results/golden_ci
mkdir -p "$RES"

echo "=== [1/2] GATE BLOQUANT : recall retrieval golden 50q (hors juge) ==="
python -m src.eval.golden_ci
GATE=$?
if [ "$GATE" != "0" ]; then
  echo "[golden-ci] GATE ROUGE (exit $GATE) -- STOP : retrieval régressé par le re-embed."
  exit "$GATE"
fi

echo "=== [2/2] ALERTE NON BLOQUANTE : groundedness golden 50q (génération + juge) ==="
# golden_50.json = {questions:[...]} -> format run_battery {items:[...]}
python -c "import json,pathlib; d=json.load(open('data/golden_eval/golden_50.json')); pathlib.Path('$RES/golden_eval_set.json').write_text(json.dumps({'items':d['questions']},ensure_ascii=False))"
# H1 lot 1.3 : conditions de serving REELLES (temp 0.3 + answer_stream, le
# chemin que le front consomme). Pour un A/B de prompt a bruit minimal,
# utiliser run_battery.py sans --serving avec --temperature 0.
python $DIR/run_battery.py --eval-set $RES/golden_eval_set.json --out $RES/golden_battery.json --serving --temperature 0.3 \
  || echo "[golden-ci][alerte] génération golden incomplète (NON BLOQUANT)"
python $DIR/judge_groundedness.py --in $RES/golden_battery.json --out $RES/golden_ground.json \
  || echo "[golden-ci][alerte] juge golden incomplet (NON BLOQUANT)"
python -c "
import json, statistics
g = json.load(open('$RES/golden_ground.json'))
vals = [r['judgment'].get('groundedness') for r in g
        if isinstance(r.get('judgment'), dict) and r['judgment'].get('groundedness') is not None]
if vals:
    print(f'[golden-ci][alerte] mean groundedness {statistics.mean(vals):.3f} '
          f'sur {len(vals)} réponses asserting (NON BLOQUANT, informatif)')
else:
    print('[golden-ci][alerte] aucune réponse asserting')
" || true
echo "=== GOLDEN_CI_DONE :: gate retrieval VERT ; alerte juge ci-dessus (non bloquante) ==="
exit 0
