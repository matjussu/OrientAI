#!/usr/bin/env bash
# Deploy RECIT prod VivaTech (ordre Jarvis 2026-06-16). A LANCER PAR MATTEO via ! :
#   ! bash /home/matteo_linux/projets/OrientIA/audit_empirique_2026-06-09/deploy_recit_prod.sh
#
# Deploy DEFENSIF de origin/main a7bab74 (mode recit forme adaptative).
# Durcissements (ordre Jarvis) :
#   (1) ABORT DUR (exit 1) si l'arbre bake DEVIE d'origin/main -> ZERO deploy.
#   (2) Capture explicite de l'ID du deploiement Railway COURANT (ancre rollback) AVANT up.
# Self-contained : cd absolu, executable depuis n'importe ou (ex: /home/matteo_linux).
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA || { echo "ABORT: repo introuvable"; exit 1; }
export PATH="$HOME/.nvm/versions/node/v22.22.1/bin:$PATH"

echo "== [1/6] fetch origin =="
git fetch origin --quiet || { echo "ABORT: git fetch echoue"; exit 1; }

echo "== [2/6] GARDE-FOU DUR : code bake == origin/main a7bab74 ? =="
BAKED="src/ Dockerfile requirements.lock scripts/build_quad_subindexes.py data/processed/golden_qa_meta.json"
DRIFT=$(git diff --stat origin/main -- $BAKED)
if [ -n "$DRIFT" ]; then
  echo "$DRIFT"
  echo ">>> ABORT DUR : l'arbre bake DEVIE d'origin/main. ZERO deploy. <<<"
  exit 1
fi
echo "OK : arbre bake identique a origin/main -> $(git log -1 --format='%h %s' origin/main)"

echo "== [3/6] corpus present (le Dockerfile les COPY dans l'image) =="
for f in data/processed/formations.json data/processed/golden_qa_meta.json; do
  [ -f "$f" ] || { echo "ABORT: $f manquant (corpus requis pour l'image)"; exit 1; }
done
ls -la data/processed/formations.json data/processed/golden_qa_meta.json | awk '{print "  ", $5, $9}'

echo "== [4/6] CIBLE PROD : projet=orientia-api + env=production (anti-mauvais-link) =="
ST=$(railway status 2>&1) || { echo "ABORT: railway status echoue (link manquant)"; exit 1; }
echo "$ST" | grep -qE "Project:[[:space:]]+orientia-api"            || { echo "$ST"; echo "ABORT: projet lie != orientia-api"; exit 1; }
echo "$ST" | grep -qE "Environment:[[:space:]]+production"          || { echo "$ST"; echo "ABORT: env lie != production"; exit 1; }
echo "$ST" | grep -q  "orientia-api-production.up.railway.app"      || { echo "$ST"; echo "ABORT: URL prod non confirmee"; exit 1; }
echo "OK cible = orientia-api / production"

echo "== [5/6] ANCRE ROLLBACK : deploiements Railway AVANT up =="
echo "  >>> Le dernier SUCCESS = ancre rollback (rollback = dashboard Railway, onglet Deployments, sur cet ID). <<<"
echo "  >>> Rappel : des deploys peuvent etre FAILED (corpus hors contexte si lance sans --no-gitignore). <<<"
railway deployment list 2>&1 | head -20 || {
  echo "ABORT: 'railway deployment list' a echoue (railway link manquant, ou preciser -s <service>)."
  echo "       Pas d'ancre rollback = pas de deploy. Corrige le link puis relance."
  exit 1
}

echo "== [6/6] DEPLOY a7bab74 =="
echo "  --no-gitignore REQUIS (corpus formations.json gitignore, COPY par le Dockerfile)."
echo "  SURVEILLER la taille d'upload : doit rester petit (~35MB compresse). data/embeddings (index ~405MB)"
echo "  vit sur le VOLUME et est exclu via .railwayignore. Si l'upload part en centaines de MB -> Ctrl-C."
railway up --no-gitignore --detach
echo
echo "== DEPLOY_LANCE (--detach : ne wait PAS le healthy) =="
echo "   suivre : railway logs   |   etat : railway deployment list"
echo "   quand healthy -> ! bash audit_empirique_2026-06-09/verify_recit_prod.sh"
