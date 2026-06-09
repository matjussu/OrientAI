"""Provider promptfoo pour OrientAI.

Sert les reponses du pipeline reel DEJA calculees (battery_full.json) pour
eviter un cold-start de 40s par test. promptfoo applique alors ses assertions
de gating (la detresse doit surfacer 3114, le stress normal ne doit PAS, une
ecole fictive doit etre refusee...). Pour re-gater apres un fix de Phase A,
on regenere la batterie puis on relance `npx promptfoo eval`.

Chemin de la batterie via env PROMPTFOO_BATTERY (defaut results/battery_full.json).
"""
import json
import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BATTERY = Path(os.environ.get(
    "PROMPTFOO_BATTERY",
    _HERE.parent / "results" / "battery_full.json"))

_LOOKUP = {}
if _BATTERY.exists():
    for r in json.loads(_BATTERY.read_text()):
        _LOOKUP[r["question"].strip()] = r.get("answer") or ""


def call_api(prompt, options, context):
    answer = _LOOKUP.get((prompt or "").strip())
    if answer is None:
        return {"error": f"question absente de la batterie : {prompt[:60]!r}"}
    return {"output": answer}
