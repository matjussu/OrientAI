#!/bin/bash
# usage : juge_un.sh <lot.json> <dossier_sortie>   (banc E, protocole v0.3 section 5 ; copie du lanceur de D)
J=/home/matteo_linux/projets/OrientIA-etape-e/results/banc_e/judge
S=/tmp/claude-1000/-home-matteo-linux-projets/527a18a3-94b3-4344-abd5-281bb782718d/scratchpad/juge
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
timeout 2400 claude -p "Lot : $J/lots/${1%.json}.txt (texte multiligne : lis-le par tranches de lignes avec offset et limit)
Dossier de sortie : $J/$2/" --agents "$AG" --agent juge --model claude-opus-5-5 --effort low --setting-sources project --strict-mcp-config --disable-slash-commands --no-session-persistence --permission-mode acceptEdits --allowedTools Read Write --output-format json > $S/juge_$nom.json 2>&1
echo "$nom exit $? cle_api=$NCLE $(date +%H:%M:%S)"
