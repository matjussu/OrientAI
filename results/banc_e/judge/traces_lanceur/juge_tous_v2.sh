#!/bin/bash
# usage : juge_tous.sh <motif de lot, ex. g1_lot_> <dossier_sortie> <parallelisme>
# Saute un lot dont tous les verdicts existent déjà (reprise par tâches manquantes, complétude sur fichiers).
J=/home/matteo_linux/projets/OrientIA-etape-e/results/banc_e/judge
T=$(cd "$(dirname "$0")" && pwd)
cd $J
for l in lots/$1*.json; do
  manque=$(python3 -c "
import json,os,sys
t=json.load(open('$l'))['taches']
print(sum(not os.path.exists('$2/'+x['oid']+'.json') for x in t))")
  [ "$manque" != "0" ] && basename $l
done | xargs -P $3 -I{} $T/juge_stdin_v2.sh {} $2
