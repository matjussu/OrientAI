#!/bin/bash
# usage : juge_stdin_v2.sh <lot.json> <dossier_sortie>   (instrument multi-version, protocole v0.1 : lot passé en entier sur stdin)
# Le juge reçoit rubrique et tâches (fiches comprises) dans son contexte, sans lecture par tranches : l'outil Read
# v2 (24/09 11h55) : binaire nvm en chemin absolu et mise a jour automatique coupee. Mesure : pendant une
# reinstallation automatique du paquet nvm (11:16, 11:20, 11:49), le PATH retombait sur /usr/bin/claude 2.1.126,
# refuse par l API pour Opus 5.5 (400 claude_code_version_too_old) ; le lot echouait sans verdict.
# plafonne à 25 000 tokens par lecture et, en tranches, un juge effort low a déclaré des lectures partielles.
J=/home/matteo_linux/projets/OrientIA-concordance/results/multiversion/2026-09-25_reference/judge_v2
S=/home/matteo_linux/projets/OrientIA-concordance/results/multiversion/2026-09-25_reference/judge_v2/sorties_juges
mkdir -p $S $J/$2
cd $J
# Garde facturation : une clé API dans l'environnement ferait passer le juge sur l'API payante sans
# signal (le .env d'OrientIA en contient une). Ce lanceur ne source aucun .env ; il refuse si une clé est là.
NCLE=$(env | grep -c "^ANTHROPIC_API_KEY=")
if [ "$NCLE" != "0" ]; then echo "$(basename $1 .json) REFUS : ANTHROPIC_API_KEY present ($NCLE)"; exit 1; fi
AG=$(python3 -c "
import json
t=open('/home/matteo_linux/projets/.claude/agents/juge-aveugle.md').read()
print(json.dumps({'juge':{'description':'juge aveugle','prompt':t.split('---',2)[2].strip(),'tools':['Read','Write'],'model':'claude-opus-5-5'}}))")
nom=$(basename $1 .json)
timeout 2400 env DISABLE_AUTOUPDATER=1 /home/matteo_linux/.nvm/versions/node/v22.22.1/bin/claude -p "Le lot est entièrement contenu dans ce message, après cette ligne : ne lis aucun fichier, lis le lot ci-dessous en entier (rubrique puis chaque tâche avec toutes ses fiches).
Dossier de sortie : $J/$2/" --agents "$AG" --agent juge --model claude-opus-5-5 --effort low --setting-sources project --strict-mcp-config --disable-slash-commands --no-session-persistence --permission-mode acceptEdits --allowedTools Read Write --output-format json < $J/lots/$nom.txt > $S/juge_stdin_$nom.json 2>&1
echo "$nom exit $? cle_api=$NCLE $(date +%H:%M:%S)"
