"""A/B injection sigle corpus (J2 enrichissement) — re-embed PARTIEL + hybride réel.

BEFORE = index original (sans sigle) + BM25 sans injection (monkeypatch off).
AFTER  = index test (687 fiches re-embeddées avec sigle) + BM25 avec injection.
Métrique = fiche cible dans le top-10 du retrieval hybride de prod (no-gen).
Gate : 7+ sigles gagnent, LAS Cergy + MIAGE Paris NE bougent PAS, contrôle
(questions sans sigle) zéro régression.
"""
from __future__ import annotations
import json, os, sys, tempfile
import numpy as np
import faiss
from mistralai.client import Mistral

sys.path.insert(0, ".")
import src.rag.sigle_expand as se
from src.rag.embeddings import fiche_to_text, embed_texts_batched
from src.rag.index import build_index, save_index
from src.rag.factory import make_production_pipeline
from src.rag.intent import classify_domain_hint

for line in open(".env"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("="); os.environ.setdefault(k.strip(), v.strip())
client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
fiches = json.load(open("data/processed/formations.json"))
ORIG = "data/embeddings/formations.index"

# --- 1. re-embed PARTIEL : reconstruct original + remplace les fiches affectées ---
idx0 = faiss.read_index(ORIG)
vecs = idx0.reconstruct_n(0, idx0.ntotal)  # (52040, 1024)
affected = [i for i, f in enumerate(fiches) if se.detect_sigles_in_fiche(f)]
print(f"[reembed] {len(affected)} fiches affectées, re-embed avec sigle injecté...", flush=True)
new_texts = [fiche_to_text(fiches[i]) for i in affected]  # injection ON
new_vecs = np.asarray(embed_texts_batched(client, new_texts, batch_size=64), dtype="float32")
for j, i in enumerate(affected):
    vecs[i] = new_vecs[j]
test_index = build_index(vecs)
tmp = tempfile.NamedTemporaryFile(suffix=".index", delete=False).name
save_index(test_index, tmp)
print(f"[reembed] index test écrit ({test_index.ntotal} vecteurs) -> {tmp}", flush=True)

def low(f, *ks): return " ".join(str(f.get(k) or "") for k in ks).lower()
def rank(rr, pred, k=10):
    for i, r in enumerate(rr[:k]):
        if pred(r.get("fiche", {})): return i + 1
    return None

import src.rag.bm25_index as _bm
_REAL = se.sigle_injection_text  # la vraie fonction (capturée avant tout patch)

def measure(index_path, injection_on):
    # NB : bm25_index a importé sigle_injection_text au top-level -> on patche
    # SA référence, pas se.*. Le dense BEFORE/AFTER est porté par le choix d'index
    # (original sans sigle vs test re-embeddé), pas par ce patch.
    _bm.sigle_injection_text = _REAL if injection_on else (lambda f: "")
    p = make_production_pipeline(client, fiches)
    p.load_index_from(index_path)
    def hy(q): return p._retrieve_and_filter(question=q, k=30, domain_hint=classify_domain_hint(q), target=10, criteria=None)
    return hy

# cas sigle (sigle, ville, key-forme) + cas CONTRÔLE (sans sigle, target stable)
SIG = [("GEA","Aubière","gestion des entreprises et des administrations"),
 ("GEII","Montluçon","génie électrique et informatique"),
 ("GMP","Montluçon","génie mécanique et productique"),
 ("MMI","Vichy","multimédia et de l'"),
 ("GACO","Morlaix","gestion administrative et commerciale"),
 ("GCGP","Périgueux","génie chimique génie des procédés"),
 ("HSE","Vesoul","hygiène sécurité environnement"),
 ("CJ","SAINT MARTIN D'H","carrières juridiques"),
 ("LAS","Cergy","licence accès santé"),
 ("MIAGE","PARIS","méthodes informatiques appliquées")]
CTRL = [("BTS info Lille","taux d'accès BTS SIO à Lille", lambda f: "sio" in low(f,'nom') or ("bts" in low(f,'nom') and "informatiques" in low(f,'nom'))),
 ("Licence droit Lyon","taux d'accès licence droit à Lyon", lambda f: "droit" in low(f,'nom') and "lyon" in low(f,'ville')),
 ("Master psycho Paris","taux d'accès master psychologie à Paris", lambda f: "psycho" in low(f,'nom') and "paris" in low(f,'ville'))]

print("\n[before] index original + BM25 sans injection ...", flush=True)
hy_b = measure(ORIG, injection_on=False)
print("[after]  index test + BM25 avec injection ...", flush=True)
hy_a = measure(tmp, injection_on=True)

print(f"\n{'cas':18s} {'AVANT':6s} {'APRÈS':6s} verdict")
fails = []
for sig, ville, key in SIG:
    pred = lambda f, key=key, ville=ville: key in low(f, "nom") and ville.lower() in low(f, "ville")
    q = f"taux d'accès BUT {sig} à {ville}"
    rb, ra = rank(hy_b(q), pred), rank(hy_a(q), pred)
    v = "=" if rb == ra else ("GAIN" if (ra and (not rb or ra < rb)) else "REGRESSION")
    print(f"{sig:18s} {str(rb):6s} {str(ra):6s} {v}")
print("--- CONTRÔLE (sans sigle, doit être stable) ---")
for label, q, pred in CTRL:
    rb, ra = rank(hy_b(q), pred), rank(hy_a(q), pred)
    v = "=" if rb == ra else ("GAIN" if (ra and (not rb or ra < rb)) else "REGRESSION")
    print(f"{label:18s} {str(rb):6s} {str(ra):6s} {v}")
    if v == "REGRESSION": fails.append(label)
print("\nCONTRÔLE régression :", "AUCUNE" if not fails else f"FAIL {fails}")
os.unlink(tmp)
