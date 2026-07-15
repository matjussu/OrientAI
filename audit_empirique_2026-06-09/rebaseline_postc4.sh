#!/usr/bin/env bash
# Re-baseline post-C4 (497q) sur l'index 52040 + harnais patche (observability Step 1b).
# GO Matteo 2026-06-10 (Telegram 4449), budget ~5$. Sequence : regen (Mistral) -> juge
# (Claude Haiku temp=0) -> metrics -> gate vs baseline PRE-C4 (= lecture du delta total
# C0-C4). NE FIGE PAS la baseline : le freeze est un pas separe, apres revue du delta.
# Resume-safe de bout en bout (run_battery + judge skippent les ids deja faits).
# Lancer detache :
#   cd ~/projets/OrientIA && PYTHONPATH=. nohup bash audit_empirique_2026-06-09/rebaseline_postc4.sh \
#     > audit_empirique_2026-06-09/results/rebaseline_postc4.log 2>&1 &
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
source .venv/bin/activate
export PYTHONPATH=.

DIR=audit_empirique_2026-06-09
RES=$DIR/results
EVAL=$DIR/eval_set_full.json
BATT=$RES/battery_full_postc4.json
GROUND=$RES/groundedness_full_postc4.json
METRICS=$RES/metrics_full_postc4.json

echo "=== [0] SANITY : eval set + index C4 + fiches C1 ==="
NEVAL=$(python -c "import json;d=json.load(open('$EVAL'));it=d['items'] if isinstance(d,dict) and 'items' in d else d;print(len(it))")
echo "  eval_set_full.json : $NEVAL questions (attendu 497)"
python -c "import faiss;print('  index formations.index ntotal :',faiss.read_index('data/embeddings/formations.index').ntotal,'(attendu 52040)')"
python -c "import json;print('  fiches formations.json :',len(json.load(open('data/processed/formations.json'))),'(attendu 52040)')"
python -c "import src.observability;from langchain_mistralai.chat_models import ChatMistralAI as C;print('  harnais patche :',C._combine_llm_outputs.__name__)"

echo "=== [1] REGEN battery $NEVAL q (Mistral, pipeline production, index C4) - resume-safe ==="
python $DIR/run_battery.py --eval-set $EVAL --out $BATT

echo "=== [2] RETRY questions en erreur (purge errored -> re-run, max 3 passes) ==="
for attempt in 1 2 3; do
  NERR=$(python -c "import json;print(sum(1 for x in json.load(open('$BATT')) if x.get('error')))")
  echo "  errored=$NERR (passe $attempt)"
  [ "$NERR" = "0" ] && break
  python -c "import json;p='$BATT';json.dump([x for x in json.load(open(p)) if not x.get('error')],open(p,'w'),ensure_ascii=False,indent=2)"
  python $DIR/run_battery.py --eval-set $EVAL --out $BATT
done

echo "=== [2.5] GUARD : battery complete avant de juger ==="
NCUR=$(python -c "import json;print(len(json.load(open('$BATT'))))")
echo "  battery=$NCUR / eval=$NEVAL"
if [ "$NCUR" != "$NEVAL" ]; then
  echo "  [ABORT] battery incomplete ($NCUR != $NEVAL). Re-lance ce script (resume reprendra). Pas de juge sur set partiel."
  exit 2
fi

echo "=== [3] JUDGE groundedness $NEVAL q (Claude Haiku temp=0, cross-family) - resume-safe ==="
python $DIR/judge_groundedness.py --in $BATT --out $GROUND

echo "=== [4] COMPUTE metrics post-C4 ==="
python -c "
import sys, json; sys.path.insert(0,'$DIR')
from metrics import compute_metrics
m = compute_metrics('$BATT','$GROUND')
json.dump(m, open('$METRICS','w'), ensure_ascii=False, indent=2)
print(json.dumps(m, ensure_ascii=False, indent=2))
"

echo "=== [5] GATE vs baseline PRE-C4 (delta total C0-C4 ; LECTURE, ne fige rien) ==="
python $DIR/gate.py --battery $BATT --groundedness $GROUND \
  || echo "  (gate exit!=0 : lire le delta ci-dessus. Un ecart peut etre l'effet C4 attendu, PAS un fail auto. Revue avant freeze.)"

echo "=== REBASELINE_POSTC4_DONE :: battery+judge+metrics+gate produits. FREEZE = pas separe apres revue du delta. ==="
