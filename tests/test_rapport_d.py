"""Étape D, analyse : accord du juge, bootstrap, complétude jugée sur les fichiers (src/eval/rapport_d.py)."""
from __future__ import annotations

import json

from src.eval import rapport_d as rd


def test_kappa_accord_parfait_et_hasard():
    assert rd.kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert rd.kappa([True, True, False, False], [True, False, True, False]) == 0.0
    assert rd.kappa([False, False], [False, False]) is None  # aucune variance : pas de kappa inventé


def test_boot_identique_zero_et_ecart_detecte():
    x = {f"c{i}": {"n": 2, "erreur_factuelle": i % 2} for i in range(40)}
    assert rd.boot(x, x, "erreur_factuelle", tirages=300) == {"delta": 0.0, "ic95": [0.0, 0.0]}
    y = {k: {"n": 2, "erreur_factuelle": 2} for k in x}
    b = rd.boot(y, x, "erreur_factuelle", tirages=300)
    assert b["delta"] > 0 and b["ic95"][0] > 0


def test_completude_rougit_sur_un_tour_manquant_ou_en_erreur(tmp_path, monkeypatch):
    monkeypatch.setattr(rd, "D", tmp_path)
    monkeypatch.setattr(rd, "COMBOS", ["A-m"])
    banc = {"items": [{"id": "c1", "turns": ["q0", "q1"]}]}
    d = tmp_path / "runs/A-m"
    d.mkdir(parents=True)
    ligne = lambda t, e=None: json.dumps({"id": "c1", "turn": t, "answer": "x", "erreur": e})
    (d / "g1.jsonl").write_text(ligne(0) + "\n" + ligne(1) + "\n")
    (d / "g2.jsonl").write_text(ligne(0) + "\n")                       # un tour manquant
    c = rd.completude(banc)
    assert c["A-m/g1"]["vert"] and not c["A-m/g2"]["vert"]
    (d / "g2.jsonl").write_text(ligne(0) + "\n" + ligne(1, "429") + "\n")  # un tour en erreur
    assert not rd.completude(banc)["A-m/g2"]["vert"]
    (d / "g2.jsonl").write_text(ligne(0) + "\n" + ligne(1) + "\n" + ligne(1) + "\n")  # un doublon
    assert not rd.completude(banc)["A-m/g2"]["vert"]
