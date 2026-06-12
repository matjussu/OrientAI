#!/usr/bin/env bash
# Re-embed #2 NEUTRALISÉ (ordre 0825, option A) — dense sigle OFF.
# Le re-embed #1 a activé par effet de bord le sigle dense J2 parké (déplace MIAGE
# Paris hors top-10, cas démo). Ce re-embed #2 reconstruit l'index avec le flag
# ORIENTIA_DENSE_SIGLE ABSENT (= dense sigle OFF) -> baseline = salaire+quartiles+
# debouches #146 SANS la régression parkée. Mêmes précautions que #1 : checkpoints
# frais, backup, golden gate derrière. COÛT ~5-10$ -> validation Matteo requise.
# Lancer détaché APRÈS go Matteo :
#   cd ~/projets/OrientIA && PYTHONPATH=. nohup bash audit_empirique_2026-06-09/reembed2_neutralized_0825.sh \
#     > audit_empirique_2026-06-09/results/reembed2_0825.log 2>&1 &
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
unset ORIENTIA_DENSE_SIGLE          # GARANTIT le dense sigle OFF dans CE process
source .venv/bin/activate
export PYTHONPATH=.
DIR=audit_empirique_2026-06-09

echo "=== [0] GUARD env : dense sigle DOIT être OFF (condition Jarvis #3) ==="
python -c "
import os
assert os.environ.get('ORIENTIA_DENSE_SIGLE') is None, 'ORIENTIA_DENSE_SIGLE set -> ABORT'
from src.rag import embeddings as e
assert e._DENSE_SIGLE_INJECTION is False, 'flag dense sigle ON dans le module -> ABORT'
print('  ORIENTIA_DENSE_SIGLE absent + _DENSE_SIGLE_INJECTION=False -> dense sigle OFF (parké) OK')
" || { echo "[ABORT] guard env dense sigle"; exit 2; }

echo "=== [1] backup index re-embed#1 (sigle ON) + checkpoints FRAIS ==="
cp -n data/embeddings/formations.index data/embeddings/formations.index.reembed1-sigleON-bak 2>/dev/null \
  && echo "  backup index #1 -> formations.index.reembed1-sigleON-bak" || echo "  (backup #1 déjà présent)"
[ -d data/embeddings/_c4_checkpoints ] && mv data/embeddings/_c4_checkpoints data/embeddings/_c4_checkpoints_reembed1_bak \
  && echo "  checkpoints #1 écartés -> _c4_checkpoints_reembed1_bak (start frais)"

echo "=== [2] RE-EMBED #2 (dense sigle OFF, rebuild full 52040) ==="
python scripts/rebuild_index_c4.py

echo "=== [3] GOLDEN GATE sur le nouvel index (gratuit, hors juge) — non-régression retrieval ==="
python -m src.eval.golden_ci || { echo "[STOP] golden gate ROUGE"; exit 2; }

echo "=== [4] CONFIRMATION MIAGE/LAS restaurés (dense sigle OFF doit re-protéger MIAGE) ==="
python $DIR/check_sigle_gate_on_new_index.py 2>&1 | tail -8 || echo "  (check MIAGE non bloquant)"

echo "=== REEMBED2_NEUTRALIZED_DONE :: dense sigle OFF, golden gate VERT. Prêt pour re-gel (bash $DIR/regel_0825.sh). ==="
