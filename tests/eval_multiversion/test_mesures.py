"""Critère 1 de l'instrument : contrôle positif contre les chiffres publiés de E, périmètre d'un run partiel."""
import json

import pytest

from src.eval.battery.config import REPO
from src.eval.multiversion.lanceur import BANCS
from src.eval.multiversion.mesures import critere1, lire_banc

RUN_E = REPO / "results/banc_e/runs/C-zai-glm-5-3/g1.jsonl"


@pytest.mark.skipif(not BANCS["vertical"].exists() or not RUN_E.exists(), reason="banc vertical hors dépôt")
def test_sans_correction_redonne_exactement_le_critere_1_publie_par_e():
    # RAPPORT E section 2 : C x GLM 5.3 = 0,805, témoin 0,068 (instrument de D, sans tableaux)
    recs = [json.loads(x) for x in RUN_E.read_text().splitlines() if x.strip()]
    rep = {(r["id"], r["turn"]): r["answer"] for r in recs}
    banc = lire_banc(BANCS["vertical"])
    sans = critere1(banc, rep, tableaux=False)
    assert (round(sans["taux"], 3), round(sans["temoin_hasard"], 3), sans["attendus"]) == (0.805, 0.068, 323)
    avec = critere1(banc, rep)
    assert avec["taux"] > sans["taux"] and avec["temoin_hasard"] == sans["temoin_hasard"]


@pytest.mark.skipif(not BANCS["vertical"].exists(), reason="banc vertical hors dépôt")
def test_run_partiel_ne_compte_que_les_conversations_jouees():
    banc = lire_banc(BANCS["vertical"])
    item = banc["items"][0]
    a = item["attendus"]["chiffres"][0]
    rep = {(item["id"], t): f"{a['valeur']} {a['unite']}" for t in range(len(item["turns"]))}
    r = critere1(banc, rep)
    assert r["conversations"] == 1 and r["attendus"] < 20 and r["taux"] > 0
