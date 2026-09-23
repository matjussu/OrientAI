"""Mine les fiches CANDIDATES pour le set de pertinence (H1 lot 2.1).

Pour chaque question retrieval-pertinente du banc 497q (+ cas MIAGE),
produit une liste de candidats issus de TROIS modes INDEPENDANTS :

  - dense  : FAISS top-N (le retrieval actuel, requête embedée)
  - bm25   : lexical top-N (BM25 hybride existant)
  - lex    : matching déterministe sur nom/etablissement/ville/discipline
             (grep-like, INDEPENDANT des embeddings — capture ce que le
             dense rate, ex. finding MIAGE Lille sur phrasing salaire)

Pourquoi trois modes : labelliser uniquement les candidats du retrieval
actuel biaiserait le set vers ce que le système sait déjà trouver (on ne
pourrait jamais mesurer ce qu'il RATE). Le mode lexical déterministe est
l'anti-biais.

Sortie : scripts/relevance_set/candidates.json
  {"_meta": {corpus_sha256, ...}, "questions": [{qid, question, category,
    candidates: [{fiche_id, mode(s), nom, etablissement, ville, region, domain, extrait}]}]}

Identite d'une fiche : `idx:<position dans formations.json>` pour les trois modes
(src/eval/battery/corpus.py). Avant le 23/09, dense et bm25 rendaient `idx:-1` pour
toute fiche sans champ `id` (38 596 sur 52 040) : 382 candidats confondus en un seul.

Coût : ~390 embeddings de requêtes (~négligeable). Aucune génération.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from mistralai.client import Mistral

import src.observability  # noqa: F401
from src.eval.battery.corpus import Corpus, fiche_key
from src.rag.factory import make_production_pipeline

EVAL = REPO / "audit_empirique_2026-06-09/eval_set_full.json"
OUT = REPO / "scripts/relevance_set/candidates.json"
INDEX = REPO / "data/embeddings/formations.index"
FICHES = REPO / "data/processed/formations.json"

# Catégories qui testent le RETRIEVAL (les autres testent le scope/la génération)
RETRIEVAL_CATEGORIES = {
    "factuelle_precise", "comparaison", "edge_geo", "metier",
    "reconversion_adulte", "baseline_inscope", "mal_formulee",
}

# Cas MIAGE (finding 13/06, persistant) : la fiche MIAGE Lille doit être
# retrouvable sur le phrasing salaire. Ajoutés comme questions dédiées.
MIAGE_QUESTIONS = [
    {"id": "miage-001", "category": "factuelle_precise",
     "question": "Quel salaire net puis-je viser en sortie de Master MIAGE à Lille ?"},
    {"id": "miage-002", "category": "factuelle_precise",
     "question": "Quelles perspectives d'insertion après un Master MIAGE à l'université de Lille ?"},
    {"id": "miage-003", "category": "factuelle_precise",
     "question": "Master MIAGE Lille : taux d'admission et débouchés ?"},
]

TOP_DENSE = 20
TOP_BM25 = 20
TOP_LEX = 15

_STOP = set("""le la les un une des de du d l au aux et ou a en pour sur avec sans que qui quoi quel
quelle quels quelles est sont je tu il on nous mon ma mes ton ta tes son sa ses ce cette ces se ne pas
plus moins tres apres avant vers chez par comme faire etre avoir peut on veux dois entre aussi si dans
bac bts but master licence formation formations etudes ecole metier salaire taux acces places devenir""".split())


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _terms(question: str) -> list[str]:
    words = re.findall(r"[a-zà-ÿ]{3,}", _norm(question))
    return [w for w in words if w not in _STOP]


def _fiche_summary(fiche: dict) -> dict:
    return {
        "nom": fiche.get("nom") or fiche.get("libelle_metier") or fiche.get("nom_metier")
               or fiche.get("libelle") or fiche.get("intitule") or "",
        "etablissement": fiche.get("etablissement"),
        "ville": fiche.get("ville"),
        "region": fiche.get("region"),
        "domain": fiche.get("domain") or fiche.get("domaine"),
        "source": fiche.get("source"),
        "extrait": (str(fiche.get("text") or fiche.get("detail") or ""))[:200],
    }


def lexical_candidates(question: str, fiches: list[dict]) -> list[tuple[int, float]]:
    """Score déterministe : recouvrement de termes question/champs identitaires.
    Indépendant des embeddings. Retourne [(index_fiche, score)] top TOP_LEX."""
    terms = _terms(question)
    if not terms:
        return []
    scores: list[tuple[int, float]] = []
    for i, f in enumerate(fiches):
        hay = _norm(" ".join(
            str(f.get(k) or "") for k in
            ("nom", "etablissement", "ville", "region", "discipline", "domaine",
             "libelle_metier", "nom_metier", "libelle", "intitule", "type_diplome")
        ))
        hits = sum(1 for t in terms if t in hay)
        if hits >= 2:
            scores.append((i, hits + 0.001 * len(hay[:1])))
    scores.sort(key=lambda x: -x[1])
    return scores[:TOP_LEX]


def main() -> None:
    if not os.environ.get("MISTRAL_API_KEY"):
        for line in (REPO / ".env").read_text().splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    eval_data = json.loads(EVAL.read_text())
    items = eval_data["items"] if isinstance(eval_data, dict) else eval_data
    questions = [q for q in items if q.get("category") in RETRIEVAL_CATEGORIES]
    questions += MIAGE_QUESTIONS
    print(f"[mine] {len(questions)} questions retrieval-pertinentes")

    corpus = Corpus(FICHES)
    fiches = corpus.fiches
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from(str(INDEX))
    pipeline._build_double_subindices()
    pipeline._retrieve_with_bm25("orientation", k=1)  # warm bm25

    from src.rag.retriever import retrieve_top_k

    meta = {"corpus_sha256": corpus.sha256, "cle": "idx:<position dans formations.json>",
            "modes": {"dense": TOP_DENSE, "bm25": TOP_BM25, "lex": TOP_LEX}}
    out = []
    done_ids = set()
    if OUT.exists():
        previous = json.loads(OUT.read_text())
        corpus.assert_version(previous["_meta"]["corpus_sha256"], str(OUT))
        out = previous["questions"]
        done_ids = {r["qid"] for r in out}
        print(f"[resume] {len(done_ids)} deja minees")

    def save() -> None:
        OUT.write_text(json.dumps({"_meta": meta, "questions": out}, ensure_ascii=False, indent=1))

    for n, q in enumerate(questions):
        if q["id"] in done_ids:
            continue
        question = q["question"]
        cand: dict[str, dict] = defaultdict(lambda: {"modes": [], "best_rank": 999})

        # dense
        for rank, r in enumerate(retrieve_top_k(pipeline.client, pipeline.index, fiches, question, k=TOP_DENSE), 1):
            fiche = r.get("fiche") if isinstance(r, dict) and "fiche" in r else r
            fid = fiche_key(corpus.position_of(fiche))
            c = cand[fid]
            c["modes"].append(f"dense#{rank}")
            c["best_rank"] = min(c["best_rank"], rank)
            c["fiche"] = fiche

        # bm25
        try:
            bm = pipeline._retrieve_with_bm25(question, k=TOP_BM25)
            for rank, r in enumerate(bm, 1):
                fiche = r.get("fiche") if isinstance(r, dict) and "fiche" in r else r
                fid = fiche_key(corpus.position_of(fiche))
                c = cand[fid]
                c["modes"].append(f"bm25#{rank}")
                c["best_rank"] = min(c["best_rank"], rank)
                c["fiche"] = fiche
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] bm25 KO sur {q['id']}: {e}")

        # lexical déterministe
        for rank, (i, _s) in enumerate(lexical_candidates(question, fiches), 1):
            fid = fiche_key(i)
            c = cand[fid]
            c["modes"].append(f"lex#{rank}")
            c["best_rank"] = min(c["best_rank"], rank)
            c["fiche"] = fiches[i]

        candidates = []
        for fid, c in sorted(cand.items(), key=lambda kv: kv[1]["best_rank"]):
            f = c.get("fiche") or {}
            candidates.append({"fiche_id": fid, "modes": c["modes"], **_fiche_summary(f)})

        out.append({
            "qid": q["id"], "question": question, "category": q["category"],
            "candidates": candidates,
        })
        if (n + 1) % 20 == 0 or n == len(questions) - 1:
            save()
            print(f"[mine] {len(out)}/{len(questions)} (incremental save)")

    save()
    print(f"[done] {len(out)} questions -> {OUT}")


if __name__ == "__main__":
    main()
