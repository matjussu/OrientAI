"""Bloc A — prépare la référence AVANT (gratuit, pas d'appel API).

Filtre le run complet post-A1/A2 (battery_final + groundedness_final, code SANS
Bloc A) au sous-ensemble master/factuel (subset_A2_factuel, 220 q), et calcule
les métriques AVANT. L'APRÈS sera un run_battery réel sur le même subset avec le
fact_card Bloc A, puis gate.py --baseline metrics_avant.
"""
import json
from pathlib import Path

import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from metrics import compute_metrics  # noqa: E402

RES = HERE / "results"
sub = json.loads((HERE / "subset_A2_factuel.json").read_text())
sub_items = sub.get("items", sub) if isinstance(sub, dict) else sub
sub_ids = {q["id"] for q in sub_items}

battery = [r for r in json.loads((RES / "battery_final.json").read_text()) if r["id"] in sub_ids]
ground = [r for r in json.loads((RES / "groundedness_final.json").read_text()) if r["id"] in sub_ids]

b_path = RES / "bloc_a_battery_avant.json"
g_path = RES / "bloc_a_groundedness_avant.json"
b_path.write_text(json.dumps(battery, ensure_ascii=False, indent=2))
g_path.write_text(json.dumps(ground, ensure_ascii=False, indent=2))

metrics = compute_metrics(str(b_path), str(g_path))
(RES / "bloc_a_metrics_avant.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2))

print(f"AVANT subset : {len(battery)} battery, {len(ground)} groundedness")
print(json.dumps({k: v for k, v in metrics.items() if not k.endswith("_ids")},
                 ensure_ascii=False, indent=2))
