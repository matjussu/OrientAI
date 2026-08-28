#!/bin/bash
# scripts/launch_qa_gen_nuit.sh — Sprint 9-data Ordre 2/2
#
# Lance la génération 1000 Q&A en tmux session detachable (background).
# Surveillance Jarvis : `tmux attach -t qa-gen` pour reattach.
#
# Usage :
#   bash scripts/launch_qa_gen_nuit.sh                # défauts (parallel=3, target=1020)
#   bash scripts/launch_qa_gen_nuit.sh 5 1020         # parallel=5 (Max 20x), target=1020
#   bash scripts/launch_qa_gen_nuit.sh 2 500          # parallel=2 (Max 5x), target=500 (fallback)
#
# Variables d'environnement (override CLI possibles) :
#   QA_PARALLEL=1               # sub-agents simultanés (défaut 1 v3 économie quota)
#   QA_TARGET=1020              # cap nb total Q&A
#   QA_MODEL_RESEARCH=claude-haiku-4-5   # Phase 1 (v3 stratégie hybride)
#   QA_MODEL_DRAFT=claude-opus-4-7       # Phase 2
#   QA_MODEL_CRITIQUE_REFINE=claude-opus-4-7  # Phase 3+4 fusion
#   QA_MODEL=claude-opus-4-7    # legacy v1+v2 (utilisé si phase-specific vides)
#   QA_RATE_DELAY=2.0           # délai entre calls subprocess (v3 sage)
#   QA_MAX_RETRIES=3            # retries sur 429 + Claude Max plan signatures
#   QA_SKIP_DECISIONS=keep,flag # mode drops-only nuit 2+ : skip uniquement
#                                 les valides du JSONL existant, refait les drops.
#                                 Default vide = comportement original.
#
# Logs : logs/golden_qa_gen_v1_YYYYMMDD_HHMMSS.log
# Output : data/golden_qa/golden_qa_v1.jsonl (append-only, resumable)
#
# Stop : `tmux send-keys -t qa-gen C-c` (graceful shutdown via SIGINT handler)
#   ou `tmux kill-session -t qa-gen` (hard kill — ne pas faire en prod)

set -euo pipefail

# CD sur le repo OrientIA (resolve relatif au script)
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR"

# Args / env
# Args positionnels avec défauts v3 (parallel 1 + target 1020 conformes
# décision Matteo Option A étalée + stratégie hybride économie quota)
QA_PARALLEL="${1:-${QA_PARALLEL:-1}}"
QA_TARGET="${2:-${QA_TARGET:-1020}}"

# Stratégie hybride v3 — 3 modèles selon criticité phase
QA_MODEL_RESEARCH="${QA_MODEL_RESEARCH:-claude-haiku-4-5}"
QA_MODEL_DRAFT="${QA_MODEL_DRAFT:-claude-opus-4-7}"
QA_MODEL_CRITIQUE_REFINE="${QA_MODEL_CRITIQUE_REFINE:-claude-opus-4-7}"

# Legacy `--model` (utilisé seulement si les 3 phase-specific NE sont PAS fournis)
QA_MODEL="${QA_MODEL:-}"

QA_RATE_DELAY="${QA_RATE_DELAY:-2.0}"
QA_MAX_RETRIES="${QA_MAX_RETRIES:-3}"
QA_SKIP_DECISIONS="${QA_SKIP_DECISIONS:-}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="logs/golden_qa_gen_v1_${TIMESTAMP}.log"
OUTPUT_JSONL="data/golden_qa/golden_qa_v1.jsonl"
CONFIG_YAML="config/diverse_prompts_50.yaml"

mkdir -p logs data/golden_qa

# Sanity checks pré-launch
if ! command -v tmux &> /dev/null; then
    echo "❌ tmux non installé — apt install tmux" >&2
    exit 1
fi

if [[ ! -f "$CONFIG_YAML" ]]; then
    echo "❌ Config YAML absente : $CONFIG_YAML" >&2
    exit 1
fi

if [[ ! -d ".venv" ]]; then
    echo "❌ .venv absent — créer avec python -m venv .venv && pip install -r requirements.lock" >&2
    exit 1
fi

# Tuer la session qa-gen existante si présente (avec confirm)
if tmux has-session -t qa-gen 2>/dev/null; then
    echo "⚠️  Session tmux 'qa-gen' déjà active. Kill ? [y/N]"
    read -r REPLY
    if [[ "$REPLY" =~ ^[Yy]$ ]]; then
        tmux kill-session -t qa-gen
    else
        echo "Aborted (lance avec un autre nom de session ou kill manuellement)."
        exit 1
    fi
fi

# Construit la commande python avec flags v3 hybrides
MODEL_FLAGS="--model-research $QA_MODEL_RESEARCH \
    --model-draft $QA_MODEL_DRAFT \
    --model-critique-refine $QA_MODEL_CRITIQUE_REFINE"

# Si l'utilisateur a explicitement set QA_MODEL legacy (rare cas downgrade v1+v2),
# on l'ajoute aussi (sera fallback si phase-specific None mais ils sont fournis ici)
if [[ -n "$QA_MODEL" ]]; then
    MODEL_FLAGS="$MODEL_FLAGS --model $QA_MODEL"
fi

# Mode drops-only nuit 2+ : propage --skip-decisions si fourni
SKIP_DECISIONS_FLAG=""
if [[ -n "$QA_SKIP_DECISIONS" ]]; then
    SKIP_DECISIONS_FLAG="--skip-decisions $QA_SKIP_DECISIONS"
fi

LIFECYCLE_LOG="logs/qa_gen_lifecycle_${TIMESTAMP}.json"

# Sprint 9 nuit 3 : trap-like lifecycle capture (apprentissage capitalisé
# `feedback_long_running_jobs.md` post-incident silent stop nuit 2 H+5).
# Capture exit code + cause + records produits dans un fichier JSON
# lisible directement au matin (vs tail log long). Jarvis check via
# session-resume au réveil.
CMD="cd '$REPO_DIR' && \
source .venv/bin/activate && \
python scripts/generate_golden_qa_v1.py \
    --config $CONFIG_YAML \
    --output $OUTPUT_JSONL \
    --parallel $QA_PARALLEL \
    --target $QA_TARGET \
    --rate-limit-delay $QA_RATE_DELAY \
    --max-retries $QA_MAX_RETRIES \
    $MODEL_FLAGS \
    $SKIP_DECISIONS_FLAG \
    2>&1 | tee $LOG_FILE; \
EXIT_CODE=\${PIPESTATUS[0]}; \
RECORDS=\$(wc -l < $OUTPUT_JSONL 2>/dev/null || echo 0); \
TS=\$(date -Iseconds); \
case \$EXIT_CODE in \
    0) CAUSE=success ;; \
    130) CAUSE=SIGINT_Ctrl_C ;; \
    143) CAUSE=SIGTERM ;; \
    *) CAUSE=error_code_\$EXIT_CODE ;; \
esac; \
printf '{\"timestamp\":\"%s\",\"exit_code\":%s,\"cause\":\"%s\",\"records_total\":%s,\"log_file\":\"%s\"}\n' \"\$TS\" \"\$EXIT_CODE\" \"\$CAUSE\" \"\$RECORDS\" \"$LOG_FILE\" > $LIFECYCLE_LOG; \
echo \"==> EXIT \$EXIT_CODE | CAUSE \$CAUSE | RECORDS \$RECORDS | lifecycle: $LIFECYCLE_LOG\" | tee -a $LOG_FILE"

echo "==> Lancement tmux session 'qa-gen' (Sprint 9-data v3 stratégie hybride)"
echo "    parallel: $QA_PARALLEL, target: $QA_TARGET"
echo "    models : research=$QA_MODEL_RESEARCH | draft=$QA_MODEL_DRAFT | critique-refine=$QA_MODEL_CRITIQUE_REFINE"
[[ -n "$QA_MODEL" ]] && echo "    legacy --model: $QA_MODEL (fallback)"
echo "    rate_limit_delay: ${QA_RATE_DELAY}s, max_retries: $QA_MAX_RETRIES"
[[ -n "$QA_SKIP_DECISIONS" ]] && echo "    🌙 skip-decisions: $QA_SKIP_DECISIONS (mode drops-only)"
echo "    log: $LOG_FILE"
echo "    lifecycle JSON: $LIFECYCLE_LOG (capture exit code + cause + records au matin)"
echo "    output: $OUTPUT_JSONL"
echo

tmux new-session -d -s qa-gen "$CMD"

echo "✅ Session 'qa-gen' lancée en background."
echo
echo "Commands utiles :"
echo "  tmux attach -t qa-gen        # reattach pour observer"
echo "  tmux send-keys -t qa-gen C-c # graceful shutdown (SIGINT)"
echo "  tmux kill-session -t qa-gen  # hard kill (à éviter)"
echo "  tail -f $LOG_FILE            # tail logs en background"
echo "  wc -l $OUTPUT_JSONL          # progression Q&A produites"
echo
echo "Surveillance Jarvis :"
echo "  - Check 01h : qualité 30-50 premiers Q&A"
echo "  - Check 04h : stats keep/flag/drop + rythme"
echo "  - Stop conditions : drop >30% / rate limit / divergence"
echo "  - Report matin 7h"
