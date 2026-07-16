#!/usr/bin/env bash
# Deploy LOT 1 H1 prod (ordre Jarvis 2026-07-16-0905). A LANCER PAR MATTEO via ! :
#   ! bash /home/matteo_linux/projets/OrientIA/audit_empirique_2026-06-09/deploy_lot1_h1_prod.sh
#
# Deploy DEFENSIF de origin/main b1be983 (lot 1 complet : R8/R9 servies,
# citation check, pins modeles, provenance, RequestTrace).
# Pattern deploy_recit_prod.sh du 16/06 (garde-fous valides) :
#   (1) ABORT DUR si l'arbre bake DEVIE d'origin/main -> ZERO deploy.
#   (2) Ancre rollback : ID du deploiement Railway COURANT capture AVANT up.
#   (3) NOUVEAU lot 1 : validation post-deploy par FINGERPRINT de provenance
#       (le /health doit exposer le hash prompt attendu 601adcee86b9 et les
#       modeles pinnes) puis 1 vraie question e2e. Un /health vert ne suffit
#       plus jamais (lecon panne 15/07).
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA || { echo "ABORT: repo introuvable"; exit 1; }
export PATH="$HOME/.nvm/versions/node/v22.22.1/bin:$PATH"

EXPECTED_SHA="b1be983"
EXPECTED_PROMPT_HASH="601adcee86b9"
EXPECTED_MODEL_GEN="mistral-medium-2604"

echo "== [1/7] fetch origin =="
git fetch origin --quiet || { echo "ABORT: git fetch echoue"; exit 1; }
git log -1 --format='%h %s' origin/main | grep -q "^$EXPECTED_SHA" \
  || { echo "ABORT: origin/main n'est plus $EXPECTED_SHA (re-generer ce script)"; exit 1; }

echo "== [2/7] GARDE-FOU DUR : code bake == origin/main $EXPECTED_SHA ? =="
BAKED="src/ Dockerfile requirements.lock scripts/build_quad_subindexes.py data/processed/golden_qa_meta.json"
DRIFT=$(git diff --stat origin/main -- $BAKED)
if [ -n "$DRIFT" ]; then
  echo "$DRIFT"
  echo ">>> ABORT DUR : l'arbre bake DEVIE d'origin/main. ZERO deploy. <<<"
  exit 1
fi
echo "OK : arbre bake identique a origin/main -> $(git log -1 --format='%h %s' origin/main)"

echo "== [3/7] corpus present (COPY dans l'image) =="
for f in data/processed/formations.json data/processed/golden_qa_meta.json; do
  [ -f "$f" ] || { echo "ABORT: $f manquant"; exit 1; }
done

echo "== [4/7] CIBLE PROD : projet=orientia-api + env=production =="
ST=$(railway status 2>&1) || { echo "ABORT: railway status echoue"; exit 1; }
echo "$ST" | grep -qE "Project:[[:space:]]+orientia-api"       || { echo "$ST"; echo "ABORT: projet != orientia-api"; exit 1; }
echo "$ST" | grep -qE "Environment:[[:space:]]+production"     || { echo "$ST"; echo "ABORT: env != production"; exit 1; }
echo "$ST" | grep -q  "orientia-api-production.up.railway.app" || { echo "$ST"; echo "ABORT: URL prod non confirmee"; exit 1; }

echo "== [5/7] ANCRE ROLLBACK : deploiement courant =="
railway status --json 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('  deploiement courant (ancre rollback) :', json.dumps(d.get('deployment') or d, default=str)[:200])
" || echo "  (ancre non extraite en JSON, noter l'ID depuis le dashboard avant de continuer)"
read -r -p ">> Ancre rollback notee ? Deployer le lot 1 maintenant ? (oui/NON) " GO
[ "$GO" = "oui" ] || { echo "Deploy annule."; exit 0; }

echo "== [6/7] railway up =="
railway up --detach || { echo "ABORT: railway up echoue"; exit 1; }
echo "Build lance. Attente de la bascule (max ~10 min)..."
for i in $(seq 1 60); do
  sleep 10
  H=$(curl -sf -m 5 https://orientia-api-production.up.railway.app/health || true)
  echo "$H" | grep -q "$EXPECTED_PROMPT_HASH" && break
done

echo "== [7/7] VALIDATION POST-DEPLOY (fingerprint + e2e) =="
H=$(curl -sf -m 10 https://orientia-api-production.up.railway.app/health) || { echo "ECHEC: /health injoignable -> ROLLBACK dashboard"; exit 1; }
echo "$H" | python3 -c "
import json, sys
d = json.load(sys.stdin)
p = d.get('provenance') or {}
ok = True
if p.get('prompt') != '$EXPECTED_PROMPT_HASH':
    print('ECHEC: hash prompt', p.get('prompt'), '!= attendu $EXPECTED_PROMPT_HASH'); ok = False
if p.get('model_gen') != '$EXPECTED_MODEL_GEN':
    print('ECHEC: model_gen', p.get('model_gen'), '!= attendu $EXPECTED_MODEL_GEN'); ok = False
if not d.get('pipeline_loaded') or not d.get('index_size'):
    print('ECHEC: pipeline non charge'); ok = False
print('OK /health + provenance :', json.dumps(p)) if ok else sys.exit(1)
"
echo "Validation e2e : demander a Claudette de rejouer sa question e2e navigateur"
echo "(orientai-platform.fr, reponse generee + sources + verdict) et de verifier le"
echo "canary au prochain tick. En cas d'echec : rollback via le dashboard Railway"
echo "sur l'ancre notee en [5/7]."
echo "DEPLOY LOT 1 TERMINE COTE PUSH."
