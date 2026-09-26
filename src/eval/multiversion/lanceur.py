"""Joue une version sur un banc : `<tag>/<version>__<banc>.jsonl`, un tour par ligne, reprise par conversation.

Budget (protocole section 7) : registre `<tag>/budget.json`, somme de tous les runs du tag par fournisseur. Avant
chaque conversation, le lanceur s'arrête si cumulé + coût de la conversation la plus chère déjà vue (sur ce
fournisseur) dépasse le plafond. Un tour sans usage mesuré compte « non mesuré » : si c'est le cas, le lanceur
s'arrête aussi, puisqu'il ne peut plus garantir le plafond.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.eval.battery.config import PRICES, REPO
from src.eval.battery.runner import code_state, complete_conversations, read_jsonl

BANCS = {
    "vertical": Path.home() / "projets/_orientai-ref/verticale-2026-09/battery_verticale.json",
    "lot0": REPO / "src/eval/battery/battery.json",
    # Gate F du cerveau v2 (contrat du cerveau, section 9), écrit avant le code (étape 3).
    "gatef": REPO / "docs/cerveau/gate_f/requetes_gate_f.json",
}
# sha256 fixés au protocole (section 3) : un banc modifié n'est pas le même instrument.
BANCS_SHA = {"vertical": "f467374be3d7", "lot0": "5b268bf34d91", "gatef": "5c78dc6e9001"}
RESULTATS = REPO / "results/multiversion"
PLAFONDS_USD = {"openai": 9.5, "mistral": 8.0}  # protocole v0.3, plafond OpenAI date du 25/09 12h04


def fournisseur(modele: str) -> str:
    if modele.startswith(("gpt", "openai")):
        return "openai"
    if modele.startswith(("mistral", "zai", "magistral", "codestral")):
        return "mistral"
    if modele.startswith("claude"):
        return "anthropic"
    raise ValueError(f"fournisseur inconnu pour {modele}")


def cout(usage: dict) -> tuple[float, int]:
    """(coût USD au prix publié, nombre d'appels non mesurés). Un modèle sans prix connu lève une erreur."""
    total, non_mesures = 0.0, 0
    for modele, u in usage.items():
        if modele not in PRICES:
            raise ValueError(f"pas de prix publié pour {modele} : l'ajouter à config.PRICES avant de jouer")
        pin, pout = PRICES[modele]
        total += (u.get("entree", 0) * pin + u.get("sortie", 0) * pout) / 1e6
        non_mesures += u.get("non_mesures", 0)
    return total, non_mesures


def charger_banc(nom: str) -> tuple[list[dict], str]:
    p = BANCS[nom]
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    if not sha.startswith(BANCS_SHA[nom]):
        raise SystemExit(f"banc {nom} modifié : sha {sha[:12]}, protocole {BANCS_SHA[nom]}")
    doc = json.loads(p.read_text(encoding="utf-8"))
    if nom == "gatef":
        # Le gate F écrit ses tours sous « tours » : lus comme les « turns » des bancs, rien d'autre ne change.
        return [{"id": q["id"], "persona": "gate_f", "domaine": q.get("domaine"), "tags": [q["famille"]],
                 "turns": q["tours"]} for q in doc["questions"]], sha
    return doc["items"], sha


class Budget:
    def __init__(self, dossier: Path, plafonds: dict[str, float] = PLAFONDS_USD):
        self.chemin = dossier / "budget.json"
        self.plafonds = plafonds
        self.verrou = threading.Lock()
        self.etat = (json.loads(self.chemin.read_text()) if self.chemin.exists()
                     else {"plafonds_usd": plafonds, "depense_usd": {}, "max_conversation_usd": {},
                           "non_mesures": 0, "runs": [], "estimations": []})

    def _ecrire(self) -> None:
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self.chemin.write_text(json.dumps(self.etat, ensure_ascii=False, indent=1) + "\n")

    def cout_connu(self, fournisseurs: set[str]) -> bool:
        with self.verrou:
            return all(f in self.etat["max_conversation_usd"] for f in fournisseurs if f in self.plafonds)

    def peut_jouer(self, fournisseurs: set[str], en_vol: int = 0) -> str | None:
        """None si la conversation suivante tient sous chaque plafond, les `en_vol` conversations déjà lancées
        comptées chacune au coût de la plus chère vue ; sinon la raison de l'arrêt."""
        with self.verrou:
            if self.etat["non_mesures"]:
                return f"{self.etat['non_mesures']} appel(s) sans usage mesuré : plafond non garanti"
            for f in fournisseurs:
                if f not in self.plafonds:
                    continue
                prevu = (self.etat["depense_usd"].get(f, 0.0)
                         + (en_vol + 1) * self.etat["max_conversation_usd"].get(f, 0.0))
                if prevu > self.plafonds[f]:
                    return (f"{f} : dépensé {self.etat['depense_usd'].get(f, 0.0):.3f} + conversation max "
                            f"{self.etat['max_conversation_usd'].get(f, 0.0):.3f} > plafond {self.plafonds[f]}")
        return None

    def ajouter_conversation(self, par_fournisseur: dict[str, float], non_mesures: int) -> None:
        with self.verrou:
            for f, v in par_fournisseur.items():
                self.etat["depense_usd"][f] = round(self.etat["depense_usd"].get(f, 0.0) + v, 6)
                self.etat["max_conversation_usd"][f] = max(self.etat["max_conversation_usd"].get(f, 0.0), v)
            self.etat["non_mesures"] += non_mesures
            self._ecrire()

    def ajouter_hors_tours(self, libelle: str, usage: dict) -> float:
        c, nm = cout(usage)
        par_f: dict[str, float] = {}
        for modele, u in usage.items():
            pin, pout = PRICES[modele]
            f = fournisseur(modele)
            par_f[f] = par_f.get(f, 0.0) + (u.get("entree", 0) * pin + u.get("sortie", 0) * pout) / 1e6
        with self.verrou:
            for f, v in par_f.items():
                self.etat["depense_usd"][f] = round(self.etat["depense_usd"].get(f, 0.0) + v, 6)
            self.etat["non_mesures"] += nm
            self.etat["runs"].append({"hors_tours": libelle, "usage": usage, "cout_usd": round(c, 6)})
            self._ecrire()
        return c

    def journal(self, entree: dict) -> None:
        with self.verrou:
            self.etat["runs"].append(entree)
            self._ecrire()


def _jouer_conversation(version, item: dict, banc: str) -> list[dict]:
    history: list[dict] = []
    tours = []
    for turn, question in enumerate(item["turns"]):
        t0 = time.time()
        try:
            r, erreur = version.ask(question, history), None
            if not (r.get("reponse") or "").strip():
                # L'usage et la trace d'une réponse vide sont gardés : jetés, le coût du tour disparaissait du
                # registre (constaté au palier 0 du v2, 25/09).
                vide = RuntimeError("reponse vide")
                vide.usage, vide.trace = r.get("usage") or {}, r.get("trace") or {}
                raise vide
        except Exception as e:  # noqa: BLE001 - une panne n'arrête pas le banc, elle est gardée et comptée
            r = {"reponse": "", "sources": [], "source_positions": [], "usage": getattr(e, "usage", {}) or {},
                 "trace": getattr(e, "trace", {}) or {}}
            erreur = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-800:]}"
        c, nm = cout(r.get("usage") or {})
        tours.append({"id": item["id"], "turn": turn, "persona": item["persona"], "domaine": item.get("domaine"),
                      "tags": item.get("tags", []), "question": question, "history": list(history),
                      "latency_s": round(time.time() - t0, 2), "error": erreur, "version": version.nom,
                      "banc": banc, "answer": r.get("reponse") or "", "sources": r.get("sources") or [],
                      "source_positions": r.get("source_positions") or [], "usage": r.get("usage") or {},
                      "appels": r.get("appels"), "cout_usd": round(c, 6), "non_mesures": nm,
                      "trace": r.get("trace") or {}, "model": r.get("modele")})
        history = history + [{"role": "user", "content": question},
                             {"role": "assistant", "content": r.get("reponse") or "(erreur)"}]
    return tours


def jouer(version, banc: str, tag: str, limite: list[str] | None = None, log=print,
          empreinte_attendue: dict | None = None, plafonds: dict[str, float] = PLAFONDS_USD,
          budget_tag: str | None = None) -> dict:
    """`budget_tag` : registre de budget d'un autre tag (l'essai à blanc compte dans le budget de la référence)."""
    items, sha = charger_banc(banc)
    dossier = RESULTATS / tag
    dossier.mkdir(parents=True, exist_ok=True)
    code = code_state()
    empreinte = version.empreinte()
    if empreinte_attendue is not None and empreinte != empreinte_attendue:
        raise SystemExit(f"empreinte de {version.nom} différente de l'attendue :\n{empreinte}\n{empreinte_attendue}")
    budget = Budget(RESULTATS / (budget_tag or tag), plafonds)
    if hasattr(version, "chauffer") and getattr(version, "chauffe", None) is None:
        budget.ajouter_hors_tours(f"chauffe {version.nom}", version.chauffer())

    sortie = dossier / f"{version.nom}__{banc}.jsonl"
    existants = read_jsonl(sortie)
    faites = complete_conversations(existants, items)
    voulues = set(limite) if limite else {it["id"] for it in items}
    todo = [it for it in items if it["id"] in voulues and it["id"] not in faites]
    rejouees = {it["id"] for it in todo}
    gardes = [r for r in existants if r["id"] not in rejouees]
    if len(gardes) < len(existants):
        sortie.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in gardes))
    fournisseurs = {fournisseur(m) for m in version.modeles}
    log(f"[{version.nom} x {banc}] {len(todo)} conversations à jouer ({len(faites)} déjà faites)")

    arret, joues, erreurs, cout_run = None, 0, 0, 0.0
    run_tours: list[dict] = []
    t0 = time.time()
    verrou = threading.Lock()
    with open(sortie, "a") as fh, ThreadPoolExecutor(max_workers=version.fils) as pool:
        en_cours = set()
        file = list(todo)

        def soumettre():
            nonlocal arret
            while file and len(en_cours) < version.fils and arret is None:
                # Tant qu'aucune conversation n'a donné son coût, une seule à la fois : le garde ne sait pas
                # encore combien réserver pour celles en vol.
                if en_cours and not budget.cout_connu(fournisseurs):
                    break
                raison = budget.peut_jouer(fournisseurs, en_vol=len(en_cours))
                if raison:
                    arret = raison
                    break
                it = file.pop(0)
                en_cours.add(pool.submit(_jouer_conversation, version, it, banc))

        soumettre()
        while en_cours:
            fait = next(as_completed(en_cours))
            en_cours.discard(fait)
            tours = fait.result()
            par_f: dict[str, float] = {}
            for rec in tours:
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
                for modele, u in rec["usage"].items():
                    pin, pout = PRICES[modele]
                    f = fournisseur(modele)
                    par_f[f] = par_f.get(f, 0.0) + (u.get("entree", 0) * pin + u.get("sortie", 0) * pout) / 1e6
                with verrou:
                    joues += 1
                    erreurs += bool(rec["error"])
                    cout_run += rec["cout_usd"]
                log(f"  {'ERR' if rec['error'] else 'ok '} {rec['id']}.{rec['turn']} {rec['latency_s']}s "
                    f"{len(rec['answer'])}c fiches={len(rec['sources'])} {rec['cout_usd']:.4f}$")
            fh.flush()
            budget.ajouter_conversation(par_f, sum(r["non_mesures"] for r in tours))
            run_tours.extend(tours)
            # Arrêt propre à une version (v2 : pannes, garantie rouge ; CONTRAT-etape3 section 9).
            if arret is None and hasattr(version, "arret"):
                arret = version.arret(run_tours)
            soumettre()

    stats = {"at": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "version": version.nom,
             "banc": banc, "banc_sha256": sha, **code, "empreinte": empreinte, "tours_joues": joues,
             "erreurs": erreurs, "cout_usd": round(cout_run, 4), "secondes": round(time.time() - t0),
             "arret": arret, "restantes": len(file) if arret else 0, "fichier": sortie.name}
    budget.journal(stats)
    log(json.dumps(stats, ensure_ascii=False))
    return stats
