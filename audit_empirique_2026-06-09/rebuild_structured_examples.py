"""Re-dérive les exemples structurés PAR FORMAT depuis le LOT déjà généré.

Le gate capturait le 1er exemple par format -> tombait parfois sur un refus
(R05/R08, retrieval vide). Ici on re-parse (parser déterministe, gratuit) TOUS
les récits du LOT et on garde, pour chaque format, l'exemple au MEILLEUR
parse_confidence = contrat front propre. Ne régénère RIEN (LOT stable).
"""
from __future__ import annotations

import json
import re

from src.rag.narrative_format import FormatDecision
from src.rag.narrative_structured import parse_narrative_response

LOT = "audit_empirique_2026-06-09/results/gate_narrative_forme_LOT.md"
OUT = "audit_empirique_2026-06-09/results/gate_narrative_forme_structured.json"

text = open(LOT, encoding="utf-8").read()
# Coupe au début de la synthèse pour ne pas parser les métriques.
text = text.split("\n# SYNTHÈSE GATES", 1)[0]

chunks = re.split(r"\n## ([RT]\d+) ", text)
best: dict[str, dict] = {}
for i in range(1, len(chunks), 2):
    rid, body = chunks[i], chunks[i + 1]
    m = re.search(r"format routé: `([a-z]+)`", body)
    if not m:
        continue  # court-circuit détresse
    fmt = m.group(1)
    anchor = "anchor" in (re.search(r"overlays=\[([^\]]*)\]", body) or re.match("", "")).group(1) if re.search(r"overlays=\[([^\]]*)\]", body) else False
    ov = re.search(r"overlays=\[([^\]]*)\]", body)
    ovs = ov.group(1) if ov else ""
    dec = FormatDecision(format=fmt, anchor_constraint=("anchor" in ovs), reassure=("reassure" in ovs))
    # Les réponses contiennent des `---` INTERNES (séparateurs de sections) ; le
    # terminateur de récit est le DERNIER `---` du chunk. On prend tout après le
    # marqueur « Réponse brute » (ligne RID retirée) puis on retire le `---` final.
    if "### Réponse brute" not in body:
        continue
    answer = body.split("### Réponse brute", 1)[1]
    answer = answer.split("\n", 1)[1] if "\n" in answer else answer  # drop ligne « RID »
    answer = answer.strip()
    if answer.endswith("---"):
        answer = answer[:-3].strip()
    parsed = parse_narrative_response(answer, dec)
    parsed["_example_recit"] = rid
    cur = best.get(fmt)
    if cur is None or parsed["parse_confidence"] > cur["parse_confidence"]:
        best[fmt] = parsed

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(best, fh, ensure_ascii=False, indent=2)

for fmt, p in best.items():
    roles = [b["role"] for b in p["blocks"]]
    has_table = any(b.get("table") for b in p["blocks"])
    print(f"{fmt:13s} ex={p['_example_recit']} conf={p['parse_confidence']} blocks={roles} table={has_table}")
