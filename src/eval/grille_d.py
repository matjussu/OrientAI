"""Étape D : joue une combinaison format × modèle sur le banc vertical (protocole PROTOCOLE.md v0.1).

    python -m src.eval.grille_d run --format A --modele mistral-medium-2604 --generation 1
    python -m src.eval.grille_d sonde            # sonde outil du format C (protocole §6)

Chaque combinaison relit la même exposition gelée (`exposition.json`), le même prompt
(`SYSTEM_PROMPT_CTX` du banc) et la même température ; seul le bloc <fiches> change selon le format.
Sorties : results/donnee_etape_d/runs/<format>-<modele>/g<n>.jsonl (un tour par ligne, reprise sur les
tours déjà joués) et manifest.json (commit, sha du banc, de la base, du corpus et de l'exposition,
modèle rendu, tokens, coût, durée). Le run s'arrête si le modèle rendu par l'API diffère du modèle
demandé (piège mesuré le 23/09 : l'alias zai-glm-5 pointe vers GLM 5.3).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.base_c.outils import Base
from src.eval.battery.config import HISTORY_WINDOW, SYSTEM_PROMPT_CTX
from src.eval.exposition_d import BANC
from src.eval.format_d import Formats

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "results/donnee_etape_d"
BASE = RACINE / "data/processed/base_etape_c.sqlite"
CORPUS = RACINE / "data/processed/formations_etape_b2.json"
EXPOSITION = SORTIE / "exposition.json"

MODELES = ("mistral-medium-2604", "mistral-large-2512", "zai-glm-5-2")
FORMATS = ("A", "B", "C")
TEMPERATURE = 0.3
MAX_APPELS_OUTIL = 4
TIMEOUT_MS = 180_000

# USD par million de tokens (entrée, sortie). Suivi budgétaire, jamais une mesure (protocole §9).
PRIX = {
    "mistral-large-2512": ((0.5, 1.5), "mistral.ai/pricing lu le 23/09, exemple de la FAQ, version non précisée"),
    "mistral-medium-2604": ((0.4, 2.0), "supposé (config du banc), non publié sur la page lue le 23/09"),
    "zai-glm-5-2": ((1.0, 4.0), "supposé, borne prudente : aucun prix publié trouvé le 23/09"),
}

PHRASE_OUTIL = ("\n\nChaque fiche ci-dessous est une carte courte. Pour lire la fiche complète d'une formation "
                "(tous ses chiffres, sessions, sources et définitions), appelle l'outil lire_fiche avec son "
                "identifiant (par exemple \"psup:7596\").")
OUTIL = [{"type": "function", "function": {
    "name": "lire_fiche",
    "description": "Rend la fiche complète d'une formation listée dans <fiches> : chaque chiffre avec sa "
                   "session, sa source et sa définition.",
    "parameters": {"type": "object", "properties": {"id": {"type": "string", "description": "identifiant de la "
                   "fiche, tel qu'écrit entre crochets, ex. psup:7596"}}, "required": ["id"]}}}]
FICHE_ABSENTE = "fiche non disponible dans ce contexte"

SONDE = ("V-INF-01", "V-SAN-08", "V-MAT-03", "V-INF-21", "V-SAN-17")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def texte_reponse(message) -> tuple[str, int]:
    """Texte rendu à l'élève, et longueur du raisonnement éventuel (jamais montré, compté)."""
    c = message.content
    if isinstance(c, str) or c is None:
        return c or "", 0
    texte, pensee = [], 0
    for part in c:
        t = getattr(part, "type", None) or (part.get("type") if isinstance(part, dict) else None)
        if t == "text":
            texte.append(getattr(part, "text", None) or part.get("text", ""))
        else:
            pensee += len(json.dumps(getattr(part, "model_dump", lambda: part)(), ensure_ascii=False, default=str))
    return "".join(texte), pensee


class Joueur:
    def __init__(self, format_: str, modele: str, formats: Formats, exposition: dict):
        from mistralai.client import Mistral
        self.format, self.modele, self.formats, self.exposition = format_, modele, formats, exposition
        self.client = Mistral(api_key=os.environ["MISTRAL_API_KEY"], timeout_ms=TIMEOUT_MS)
        self.precalculer(sorted({i for c in exposition["conversations"].values() for i in c["exposees"]}))

    def precalculer(self, ids: list[str]) -> None:
        """Rendus calculés dans le fil principal : la connexion SQLite ne se partage pas entre fils."""
        self.rendus = {"A": {i: f"[fiche {i}]\n{self.formats.texte_a(i)}" for i in ids},
                       "B": {i: self.formats.carte_b(i) for i in ids},
                       "C": {i: self.formats.carte_c(i) for i in ids}}

    def bloc_fiches(self, ids: list[str]) -> str:
        if not ids:
            return "\n\n<fiches>(aucune fiche pour cette question)</fiches>"
        corps = "\n\n---\n\n".join(self.rendus[self.format][i] for i in ids)
        return (PHRASE_OUTIL if self.format == "C" else "") + f"\n\n<fiches>\n{corps}\n</fiches>"

    def outil(self, ids: list[str], args) -> tuple[str, str | None]:
        try:
            args = json.loads(args) if isinstance(args, str) else (args or {})
            id_ = str(args.get("id", "")).strip().strip("[]")
        except (ValueError, AttributeError):
            return "erreur : arguments illisibles, attendu {\"id\": \"psup:7596\"}", "arguments_invalides"
        if id_ not in ids:
            return FICHE_ABSENTE, "identifiant_inconnu"
        return self.rendus["B"][id_], None

    def tour(self, systeme: str, historique: list[dict], question: str, ids: list[str]) -> dict:
        msgs = [{"role": "system", "content": systeme}, *historique, {"role": "user", "content": question}]
        t0, tin, tout, appels, pensee = time.time(), 0, 0, [], 0
        modeles_rendus = set()
        for etape in range(MAX_APPELS_OUTIL + 1):
            avec_outil = self.format == "C" and etape < MAX_APPELS_OUTIL
            kw = {"tools": OUTIL, "tool_choice": "auto"} if avec_outil else {}
            r = self.client.chat.complete(model=self.modele, messages=msgs, temperature=TEMPERATURE, **kw)
            tin += r.usage.prompt_tokens
            tout += r.usage.completion_tokens
            modeles_rendus.add(r.model)
            m = r.choices[0].message
            texte, p = texte_reponse(m)
            pensee += p
            if not m.tool_calls:
                return {"answer": texte, "finish_reason": r.choices[0].finish_reason, "tokens_in": tin,
                        "tokens_out": tout, "secondes": round(time.time() - t0, 2), "appels_outil": appels,
                        "raisonnement_caracteres": pensee, "modeles_rendus": sorted(modeles_rendus)}
            msgs.append({"role": "assistant", "content": texte, "tool_calls": m.tool_calls})
            for tc in m.tool_calls:
                resultat, erreur = self.outil(ids, tc.function.arguments)
                appels.append({"args": tc.function.arguments if isinstance(tc.function.arguments, str)
                               else json.dumps(tc.function.arguments, ensure_ascii=False), "erreur": erreur})
                msgs.append({"role": "tool", "name": tc.function.name, "tool_call_id": tc.id, "content": resultat})
        raise RuntimeError("boucle d'outil non terminée")  # inatteignable : la dernière étape est sans outil

    def conversation(self, item: dict) -> list[dict]:
        ids = self.exposition["conversations"][item["id"]]["exposees"]
        systeme = SYSTEM_PROMPT_CTX + self.bloc_fiches(ids)
        historique, out = [], []
        for i, question in enumerate(item["turns"]):
            rec = {"id": item["id"], "turn": i, "question": question, "format": self.format, "modele": self.modele,
                   "history": historique[-HISTORY_WINDOW:], "exposees": ids}
            essais = 0
            while True:
                essais += 1
                try:
                    r = self.tour(systeme, historique[-HISTORY_WINDOW:], question, ids)
                    if r["finish_reason"] == "length" and essais == 1:
                        continue  # rejouée une fois, puis marquée (protocole §5)
                    rec.update(r, erreur="coupee" if r["finish_reason"] == "length" else None)
                    break
                except Exception as e:  # noqa: BLE001 - tracé tel quel, le tour est rejoué au prochain lancement
                    limite = "429" in str(e)
                    # 429 mesuré le 23/09 sur zai-glm-5-2 (78 tours sur 158) : attente plus longue, plus d'essais.
                    if essais < (8 if limite else 3):
                        time.sleep(min(120, 10 * 2 ** (essais - 1)) if limite else 5 * essais)
                        continue
                    rec.update(answer="", erreur=f"{type(e).__name__}: {e}")
                    break
            out.append(rec)
            historique = historique + [{"role": "user", "content": question},
                                       {"role": "assistant", "content": rec.get("answer") or ""}]
        return out


def _lire(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def jouer(format_: str, modele: str, generation: int, ids_conversations: list[str] | None = None,
          dossier: Path | None = None, workers: int = 3) -> dict:
    banc = json.loads(BANC.read_bytes())
    exposition = json.loads(EXPOSITION.read_bytes())
    base = Base.ouvrir(BASE)
    formats = Formats(base, json.loads(CORPUS.read_bytes()))
    for cle, p in (("banc_sha256", BANC), ("base_sha256", BASE), ("corpus_sha256", CORPUS)):
        if exposition[cle] != sha(p):
            raise SystemExit(f"exposition.json calculée sur un autre {cle} : {exposition[cle][:12]} contre {sha(p)[:12]}")
    joueur = Joueur(format_, modele, formats, exposition)
    dossier = dossier or SORTIE / "runs" / f"{format_}-{modele}"
    dossier.mkdir(parents=True, exist_ok=True)
    sortie = dossier / f"g{generation}.jsonl"
    # Une conversation est faite si TOUS ses tours sont joués sans erreur ; les autres sont retirées du
    # fichier et rejouées en entier (l'historique d'un tour dépend des réponses précédentes).
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
    items = [i for i in banc["items"] if (ids_conversations is None or i["id"] in ids_conversations)
             and i["id"] not in faits]
    t0 = time.time()
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
            print(f"  {futurs[fut]} : {len(recs)} tours, {sum(r.get('tokens_in', 0) for r in recs)} tokens entrée")
    recs = _lire(sortie)
    (pin, pout), note_prix = PRIX[modele]
    tin, tout = sum(r.get("tokens_in", 0) for r in recs), sum(r.get("tokens_out", 0) for r in recs)
    manifeste = {
        "format": format_, "modele": modele, "generation": generation, "protocole": "PROTOCOLE.md v0.1",
        "commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=RACINE, capture_output=True, text=True).stdout.strip(),
        "git_dirty": bool(subprocess.run(["git", "status", "--porcelain", "src"], cwd=RACINE, capture_output=True,
                                         text=True).stdout.strip()),
        "banc_sha256": exposition["banc_sha256"], "base_sha256": exposition["base_sha256"],
        "corpus_sha256": exposition["corpus_sha256"], "exposition_sha256": sha(EXPOSITION),
        "temperature": TEMPERATURE, "tours": len(recs), "erreurs": sum(bool(r.get("erreur")) for r in recs),
        "modeles_rendus": sorted({m for r in recs for m in r.get("modeles_rendus", [])}),
        "tokens_in": tin, "tokens_out": tout, "cout_usd": round((tin * pin + tout * pout) / 1e6, 4),
        "prix_usd_par_million": [pin, pout], "prix_source": note_prix,
        "secondes_tours": round(sum(r.get("secondes", 0) for r in recs), 1), "secondes_mur": round(time.time() - t0, 1),
    }
    (dossier / f"manifest_g{generation}.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=1) + "\n",
                                                          encoding="utf-8")
    return manifeste


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--format", choices=FORMATS, required=True)
    r.add_argument("--modele", choices=MODELES, required=True)
    r.add_argument("--generation", type=int, default=1)
    r.add_argument("--workers", type=int, default=3)
    sub.add_parser("sonde")
    args = ap.parse_args(argv)
    if args.cmd == "run":
        print(json.dumps(jouer(args.format, args.modele, args.generation, workers=args.workers), ensure_ascii=False,
                         indent=1))
        return 0
    for modele in MODELES:
        m = jouer("C", modele, 1, ids_conversations=list(SONDE), dossier=SORTIE / "sonde_outil" / modele)
        print(json.dumps(m, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
