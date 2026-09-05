import json, time, os, sys
os.environ.setdefault("ORIENTIA_NARRATIVE_MODE", "1")
from mistralai.client import Mistral
from src.config import load_config
from src.rag.factory import make_production_pipeline
c = load_config()
client = Mistral(api_key=c.mistral_api_key)
fiches = json.load(open("data/processed/formations.json"))
t0 = time.time()
p = make_production_pipeline(client, fiches)
p.load_index_from("data/embeddings/formations.index")
print("boot", round(time.time()-t0,1), "s", file=sys.stderr)
q = sys.argv[1] if len(sys.argv) > 1 else "Je suis en terminale générale spé maths et physique à Lyon, j'aime l'informatique mais je ne veux pas faire une prépa. Qu'est-ce que tu me conseilles ?"
t0 = time.time()
out = p.answer(q)
print("answer", round(time.time()-t0,1), "s", file=sys.stderr)
text, sources = out[0], out[1]
print(text)
print("\n--- SOURCES ---")
for s in sources[:10]:
    print("-", (s.get("nom") or s.get("title") or str(s))[:120] if isinstance(s, dict) else str(s)[:120])
