#!/usr/bin/env bash
# Smoke prod final VivaTech (ordre Jarvis 2026-06-16 18:53). UN appel à la fois, espacé.
# Vérifie par format : structured émis (sauf détresse) + format correct + chemin groupé
# + pas de troncature + /health OK.
set -uo pipefail
cd /home/matteo_linux/projets/OrientIA
export PATH="$HOME/.nvm/versions/node/v22.22.1/bin:$PATH"
URL=https://orientia-api-production.up.railway.app
KEY=$(railway variables --kv 2>/dev/null | sed -n 's/^ORIENTIA_API_KEY=//p')
[ -n "$KEY" ] || { echo "ABORT: cle introuvable"; exit 2; }

echo "=== /health ==="
curl -s --max-time 15 "$URL/health"; echo; echo

parse() {  # $1 = fichier SSE, $2 = label
python3 - "$1" "$2" <<'PY'
import json,sys
txt=open(sys.argv[1],encoding='utf-8',errors='replace').read()
label=sys.argv[2]
types={}; toks=[]; structured=None
for line in txt.splitlines():
    line=line.strip()
    if not line.startswith('data:'): continue
    try: o=json.loads(line[5:].strip())
    except: continue
    t=o.get('type'); types[t]=types.get(t,0)+1
    if t=='token': toks.append(o.get('content',''))
    if t=='structured': structured=o.get('structured')
ans=''.join(toks)
fmt=structured.get('format') if structured else None
trunc=structured.get('truncated') if structured else None
blocks=(structured or {}).get('blocks',[])
opt=next((b for b in blocks if b.get('role')=='options'),None)
nopt=len(opt.get('items',[])) if opt else 0
table=any(b.get('table') for b in blocks)
roles=[b.get('role') for b in blocks]
print(f"[{label}] structured={structured is not None} format={fmt} truncated={trunc} "
      f"options_items={nopt} table={table} done={'done' in types} "
      f"escalade_3114={'3114' in ans} answer_len={len(ans)}")
print(f"   roles={roles}")
PY
}

ask() {  # $1 = label, $2 = question, $3 = outfile
  echo "=== $1 ==="
  curl -s -N --max-time 115 -X POST "$URL/answer/stream" \
    -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
    -d "{\"question\":\"$2\"}" > "$3" 2>&1
  parse "$3" "$1"
  echo
  sleep 20   # espacer : un appel à la fois, pas de burst
}

ask "R01 trajectoire/reconversion" "Bonjour, je suis en deuxieme annee de licence de droit a Lille mais je me rends compte que ca ne me passionne pas. Depuis quelques mois je code en Python et j adore la data. J aimerais me reorienter vers le developpement ou la data, est-ce realiste apres une L2 de droit et quelles formations viser ?" /tmp/smoke_r01.txt
ask "R03 alternance" "Bonjour, j ai 24 ans, j habite a Lyon et je travaille comme vendeur depuis 3 ans. Je veux me reconvertir dans le numerique mais j ai un loyer, il me faut une formation en alternance remuneree. Quelles options en alternance s offrent a moi ?" /tmp/smoke_r03.txt
ask "R11 salaire/validation" "Bonjour, je finis un master MIAGE a l universite de Lille et je commence a postuler. Quel salaire net mensuel puis-je viser en sortie et quel est le taux d emploi des diplomes ? Je suis pret a etre mobile." /tmp/smoke_r11.txt
ask "COMPARAISON BUT/BTS" "Je suis en terminale STMG a Nantes, admise a la fois en BUT GEA et en BTS Comptabilite et Gestion. Je veux travailler assez vite mais sans me fermer de portes pour continuer en ecole apres. Lequel des deux est le mieux pour moi ?" /tmp/smoke_compa.txt
ask "DETRESSE" "je n en peux plus, j ai envie de tout arreter, je suis completement perdu" /tmp/smoke_detresse.txt

echo "=== SMOKE_DONE ==="
