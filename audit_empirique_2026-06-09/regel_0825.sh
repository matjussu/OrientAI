#!/usr/bin/env bash
# Re-gel 497q (ordre 0825 Phase 3c) sur le NOUVEL index re-embeddé.
# Mesure le delta HEAD-complet vs gel 10/06 (salaire+quartiles + sigle J2 + debouches #146
# activés en bloc par le re-embed). temp=0. Sorties FRAÎCHES regel_* (PAS gel_battery.json,
# que le resume du runner skipperait -> piège 10/06). Resume-safe de bout en bout.
# Backup du gel figé avant. NE FIGE PAS : le freeze est un pas séparé après revue du delta.
# Lancer détaché :
#   cd ~/projets/OrientIA && PYTHONPATH=. nohup bash audit_empirique_2026-06-09/regel_0825.sh \
#     > audit_empirique_2026-06-09/results/regel_0825.log 2>&1 &
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
source .venv/bin/activate
export PYTHONPATH=.
DIR=audit_empirique_2026-06-09
RES=$DIR/results
EVAL=$DIR/eval_set_full.json
BATT=$RES/regel_battery.json
GROUND=$RES/regel_ground.json

echo "=== [0] SANITY + BACKUP gel figé ==="
python -c "import faiss;n=faiss.read_index('data/embeddings/formations.index').ntotal;print('  index ntotal:',n);assert n==52040,'index != 52040'"
NEVAL=$(python -c "import json;d=json.load(open('$EVAL'));it=d['items'] if isinstance(d,dict) and 'items' in d else d;print(len(it))")
echo "  eval_set_full : $NEVAL questions (attendu 497)"
BK=$DIR/gel_bak_pre_regel_0825
mkdir -p "$BK" && cp -n $RES/gel_battery.json $RES/gel_ground.json "$BK"/ 2>/dev/null && echo "  [backup] gel figé -> $BK"

echo "=== [1] REGEN 497q sur NOUVEL index (Mistral, temp=0, resume-safe, fichier FRAIS) ==="
python $DIR/run_battery.py --eval-set $EVAL --out $BATT --temperature 0

echo "=== [2] RETRY questions en erreur (max 3 passes) ==="
for attempt in 1 2 3; do
  NERR=$(python -c "import json;print(sum(1 for x in json.load(open('$BATT')) if x.get('error')))")
  echo "  errored=$NERR (passe $attempt)"
  [ "$NERR" = "0" ] && break
  python -c "import json;p='$BATT';json.dump([x for x in json.load(open(p)) if not x.get('error')],open(p,'w'),ensure_ascii=False,indent=2)"
  python $DIR/run_battery.py --eval-set $EVAL --out $BATT --temperature 0
done

echo "=== [2.5] GUARD : battery complète avant de juger ==="
NCUR=$(python -c "import json;print(len(json.load(open('$BATT'))))")
echo "  battery=$NCUR / eval=$NEVAL"
if [ "$NCUR" != "$NEVAL" ]; then
  echo "  [ABORT] battery incomplète ($NCUR != $NEVAL). Re-lance (resume reprendra). Pas de juge sur set partiel."
  exit 2
fi

echo "=== [3] JUGE groundedness 497q (Haiku temp=0, cross-family, resume-safe) ==="
python $DIR/judge_groundedness.py --in $BATT --out $GROUND

echo "=== [4] METRICS regel vs gel figé (source de vérité compute_metrics) ==="
python -c "
import sys, json; sys.path.insert(0,'$DIR')
from metrics import compute_metrics
regel = compute_metrics('$BATT','$GROUND')
gel   = compute_metrics('$RES/gel_battery.json','$RES/gel_ground.json')
json.dump(regel, open('$RES/regel_metrics.json','w'), ensure_ascii=False, indent=2)
def line(k, fmt='{}'):
    g=gel.get(k); r=regel.get(k)
    print(f'  {k:32} gel={fmt.format(g)}  ->  regel={fmt.format(r)}')
print('--- DELTA re-gel vs gel 10/06 (HEAD complet : salaire+quartiles+sigle J2+debouches #146) ---')
line('n_questions'); line('mean_groundedness_asserting'); line('n_gradeable_asserting')
line('n_hallucinated_numbers'); line('n_metric_substitution'); line('n_answered_alternative_disclaimed')
print('  outcomes gel  :', gel.get('outcomes'))
print('  outcomes regel:', regel.get('outcomes'))
"
echo "=== REGEL_0825_DONE :: regel_battery + regel_ground + regel_metrics produits. FREEZE = pas séparé après revue Jarvis/Matteo du delta. ==="
