"""Sonde de vitesse de l'API avant les bancs (CONTRAT-etape4, amendement v1.1, section 15.2 c).

3 appels identiques à `zai-glm-5-3` (point d'accès Europe, timeout du pipeline), prompt v1, une question générale qui
n'appartient à aucun banc, sans outils. Mesure : secondes par millier de jetons de sortie, par appel, et leur médiane,
même statistique que `src.eval.multiversion.mesures.vitesse_sortie` (référence de l'étape 3 : 5,64). Seuil : 11,3 ;
au-delà, les bancs sont reportés. Chaque passage s'ajoute à `sonde_vitesse.json` avec son heure et son coût.
    python3 docs/cerveau/etape4/mesures/sonde_vitesse.py
"""
from __future__ import annotations

import datetime as dt
import json
import statistics
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RACINE))
from src.eval.battery.config import PRICES  # noqa: E402
from src.eval.grille_d import texte_reponse  # noqa: E402
from src.eval.multiversion.versions.v2 import _cle_mistral  # noqa: E402
from src.v2 import prompt as prompts  # noqa: E402
from src.v2.pipeline import MODELE, SERVEUR, TEMPERATURE, TIMEOUT_MS  # noqa: E402

SEUIL = 11.3
QUESTION = "Quelles différences entre un BTS et un BUT, en quelques phrases ?"
SORTIE = Path(__file__).with_suffix(".json")


def main() -> int:
    from mistralai.client import Mistral
    client = Mistral(api_key=_cle_mistral(), server_url=SERVEUR, timeout_ms=TIMEOUT_MS)
    msgs = [{"role": "system", "content": prompts.systeme({}, "v1")}, {"role": "user", "content": QUESTION}]
    appels, cout = [], 0.0
    for _ in range(3):
        t0 = time.time()
        r = client.chat.complete(model=MODELE, messages=msgs, temperature=TEMPERATURE)
        s = time.time() - t0
        u = r.usage
        _, pensee = texte_reponse(r.choices[0].message)
        entree_usd, sortie_usd = PRICES[MODELE]          # USD par million de jetons (entrée, sortie)
        cout += (u.prompt_tokens * entree_usd + u.completion_tokens * sortie_usd) / 1e6
        appels.append({"secondes": round(s, 2), "entree": u.prompt_tokens, "sortie": u.completion_tokens,
                       "raisonnement_caracteres": pensee, "s_par_k": round(s / (u.completion_tokens / 1000), 2)})
    med = statistics.median(a["s_par_k"] for a in appels)
    passage = {"at": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "modele": MODELE,
               "appels": appels, "mediane_s_par_k": round(med, 2), "seuil": SEUIL, "reference_etape3": 5.64,
               "verdict": "bancs possibles" if med <= SEUIL else "bancs reportés", "cout_usd_estime": round(cout, 4)}
    hist = json.loads(SORTIE.read_text()) if SORTIE.exists() else []
    SORTIE.write_text(json.dumps(hist + [passage], ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(passage, ensure_ascii=False))
    return 0 if med <= SEUIL else 1


if __name__ == "__main__":
    sys.exit(main())
