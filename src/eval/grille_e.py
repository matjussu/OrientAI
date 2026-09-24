"""Banc E : joue une combinaison format x modèle (protocole results/banc_e/PROTOCOLE.md v0.3).

    python -m src.eval.grille_e run --format A --modele mistral-small-2603 --generation 1 [--workers 3]

Réutilise le joueur de D (`grille_d.Joueur` : même prompt, même exposition gelée, même boucle d'outil, même
température) et ne change que ce que le protocole v0.3 liste en section 9 : endpoint api.eu.mistral.ai, modèles,
consigne d'outil explicite au format C, prix publiés, et un manifeste qui porte le nombre de fils et, par tour,
l'horodatage de début et de fin, le nombre d'essais et les 429 (pour mesurer enfin le débit).
Le code de D n'est pas modifié : ses runs restent rejouables à l'identique.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from src.base_c.outils import Base
from src.eval.battery.config import HISTORY_WINDOW, SYSTEM_PROMPT_CTX
from src.eval.exposition_d import BANC
from src.eval.format_d import Formats
from src.eval.grille_d import BASE, CORPUS, EXPOSITION, TIMEOUT_MS, Joueur, _lire, sha

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "results/banc_e"
SERVEUR = "https://api.eu.mistral.ai"
FORMATS = ("A", "C")

# USD par million de tokens (entrée, sortie), prix publiés lus le 24/09/2026 (protocole v0.3, section 2).
PRIX = {
    "mistral-medium-2604": ((1.5, 7.5), "docs.mistral.ai/models/mistral-medium-3-5-26-04, lu le 24/09"),
    "zai-glm-5-2": ((1.4, 4.4), "docs.mistral.ai/models/zai-glm-5-2, lu le 24/09"),
    "zai-glm-5-3": ((1.4, 4.4), "docs.mistral.ai/models/zai-glm-5-3, lu le 24/09"),
    "mistral-small-2603": ((0.15, 0.6), "docs.mistral.ai/models/mistral-small-4-0-26-03, lu le 24/09"),
}
MODELES = tuple(PRIX)

# Consigne d'outil explicite du diagnostic (results/banc_e/diag_outil/RESUME.md) : la consigne descriptive de D
# ne déclenchait jamais l'appel chez Medium (0/5), celle-ci le déclenche (3/5, négatif 0/2).
PHRASE_OUTIL_E = ("\n\nChaque fiche ci-dessous est une carte courte : elle ne contient que quelques chiffres. "
                  "Avant de répondre, appelle l'outil lire_fiche (par exemple {\"id\": \"psup:7596\"}) pour chaque "
                  "formation dont tu vas citer des chiffres, des conditions d'accès ou des débouchés : la fiche "
                  "complète donne tous ses chiffres, sessions, sources et définitions. N'appelle pas l'outil si la "
                  "question ne porte sur aucune formation.")


def maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class JoueurE(Joueur):
    def __init__(self, format_: str, modele: str, formats: Formats, exposition: dict, serveur: str = SERVEUR):
        super().__init__(format_, modele, formats, exposition)
        from mistralai.client import Mistral
        self.client = Mistral(api_key=os.environ["MISTRAL_API_KEY"], server_url=serveur, timeout_ms=TIMEOUT_MS)

    def bloc_fiches(self, ids: list[str]) -> str:
        if not ids:
            return "\n\n<fiches>(aucune fiche pour cette question)</fiches>"
        corps = "\n\n---\n\n".join(self.rendus[self.format][i] for i in ids)
        return (PHRASE_OUTIL_E if self.format == "C" else "") + f"\n\n<fiches>\n{corps}\n</fiches>"

    def conversation(self, item: dict) -> list[dict]:
        """Comme D (reprise, 429, réponse coupée rejouée une fois), plus horodatage, essais et 429 par tour."""
        ids = self.exposition["conversations"][item["id"]]["exposees"]
        systeme = SYSTEM_PROMPT_CTX + self.bloc_fiches(ids)
        historique, out = [], []
        for i, question in enumerate(item["turns"]):
            rec = {"id": item["id"], "turn": i, "question": question, "format": self.format, "modele": self.modele,
                   "history": historique[-HISTORY_WINDOW:], "exposees": ids, "debut": maintenant()}
            essais, n429 = 0, 0
            while True:
                essais += 1
                try:
                    r = self.tour(systeme, historique[-HISTORY_WINDOW:], question, ids)
                    if r["finish_reason"] == "length" and essais == 1:
                        continue
                    rec.update(r, erreur="coupee" if r["finish_reason"] == "length" else None)
                    break
                except Exception as e:  # noqa: BLE001 - tracé tel quel, le tour est rejoué au prochain lancement
                    limite = "429" in str(e)
                    n429 += limite
                    if essais < (8 if limite else 3):
                        time.sleep(min(120, 10 * 2 ** (essais - 1)) if limite else 5 * essais)
                        continue
                    rec.update(answer="", erreur=f"{type(e).__name__}: {e}")
                    break
            rec.update(fin=maintenant(), essais=essais, n429=n429)
            out.append(rec)
            historique = historique + [{"role": "user", "content": question},
                                       {"role": "assistant", "content": rec.get("answer") or ""}]
        return out


def jouer(format_: str, modele: str, generation: int, workers: int = 3, serveur: str = SERVEUR) -> dict:
    banc = json.loads(BANC.read_bytes())
    exposition = json.loads(EXPOSITION.read_bytes())
    formats = Formats(Base.ouvrir(BASE), json.loads(CORPUS.read_bytes()))
    for cle, p in (("banc_sha256", BANC), ("base_sha256", BASE), ("corpus_sha256", CORPUS)):
        if exposition[cle] != sha(p):
            raise SystemExit(f"exposition.json calculée sur un autre {cle} : {exposition[cle][:12]} contre {sha(p)[:12]}")
    joueur = JoueurE(format_, modele, formats, exposition, serveur)
    dossier = SORTIE / "runs" / f"{format_}-{modele}"
    dossier.mkdir(parents=True, exist_ok=True)
    sortie = dossier / f"g{generation}.jsonl"
    existants = _lire(sortie)
    tours = {i["id"]: len(i["turns"]) for i in banc["items"]}
    ok: dict[str, int] = {}
    for r in existants:
        if not r.get("erreur"):
            ok[r["id"]] = ok.get(r["id"], 0) + 1
    faits = {c for c, n in ok.items() if n == tours.get(c)}
    if any(r["id"] not in faits for r in existants):
        (dossier / f"g{generation}.erreurs.jsonl").open("a", encoding="utf-8").writelines(
            json.dumps(r, ensure_ascii=False) + "\n" for r in existants if r["id"] not in faits)
        sortie.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in existants if r["id"] in faits),
                          encoding="utf-8")
    items = [i for i in banc["items"] if i["id"] not in faits]
    t0, debut = time.time(), maintenant()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futurs = {pool.submit(joueur.conversation, it): it["id"] for it in items}
        for fut in as_completed(futurs):
            recs = fut.result()
            rendus = {m for r in recs for m in r.get("modeles_rendus", [])}
            if rendus - {modele}:
                pool.shutdown(cancel_futures=True)
                raise SystemExit(f"modèle rendu {sorted(rendus)} différent du modèle demandé {modele} : arrêt")
            with open(sortie, "a", encoding="utf-8") as fh:
                for r in recs:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  {futurs[fut]} : {len(recs)} tours, 429={sum(r['n429'] for r in recs)}", flush=True)
    mur = round(time.time() - t0, 1)
    recs = _lire(sortie)
    (pin, pout), note_prix = PRIX[modele]
    tin, tout = sum(r.get("tokens_in", 0) for r in recs), sum(r.get("tokens_out", 0) for r in recs)
    passage = {"workers": workers, "debut": debut, "fin": maintenant(), "secondes_mur": mur, "tours_joues": sum(
        1 for r in recs if r["id"] in {i["id"] for i in items})}
    manif_p = dossier / f"manifest_g{generation}.json"
    passages = (json.loads(manif_p.read_text(encoding="utf-8")).get("passages", []) if manif_p.exists() else [])
    passages.append(passage)
    manifeste = {
        "format": format_, "modele": modele, "generation": generation, "protocole": "results/banc_e/PROTOCOLE.md v0.3",
        "serveur": serveur,
        "commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RACINE, capture_output=True, text=True).stdout.strip(),
        "git_dirty": bool(subprocess.run(["git", "status", "--porcelain", "src"], cwd=RACINE, capture_output=True,
                                         text=True).stdout.strip()),
        "banc_sha256": exposition["banc_sha256"], "base_sha256": exposition["base_sha256"],
        "corpus_sha256": exposition["corpus_sha256"], "exposition_sha256": sha(EXPOSITION),
        "temperature": 0.3, "tours": len(recs), "erreurs": sum(bool(r.get("erreur")) for r in recs),
        "modeles_rendus": sorted({m for r in recs for m in r.get("modeles_rendus", [])}),
        "tokens_in": tin, "tokens_out": tout, "cout_usd": round((tin * pin + tout * pout) / 1e6, 4),
        "prix_usd_par_million": [pin, pout], "prix_source": note_prix,
        "n429": sum(r.get("n429", 0) for r in recs), "secondes_tours": round(sum(r.get("secondes", 0) for r in recs), 1),
        "passages": passages,
    }
    manif_p.write_text(json.dumps(manifeste, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return manifeste


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--format", choices=FORMATS, required=True)
    r.add_argument("--modele", choices=MODELES, required=True)
    r.add_argument("--generation", type=int, default=1)
    r.add_argument("--workers", type=int, default=3)
    args = ap.parse_args(argv)
    print(json.dumps(jouer(args.format, args.modele, args.generation, workers=args.workers), ensure_ascii=False,
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
