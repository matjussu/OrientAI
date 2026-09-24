import json,os,sys
from concurrent.futures import ThreadPoolExecutor
from src.eval import diag_outil_e as d
from src.eval.grille_d import PHRASE_OUTIL
from mistralai.client import Mistral
c=Mistral(api_key=os.environ["MISTRAL_API_KEY"],server_url=d.SERVEUR,timeout_ms=150_000)
banc={i["id"]:i for i in json.loads(d.BANC.read_bytes())["items"]}
S=d.systemes(list(d.SONDE))
PHRASE2=("\n\nChaque fiche ci-dessous est une carte courte : elle ne contient que quelques chiffres. "
 "Avant de répondre, appelle l'outil lire_fiche (par exemple {\"id\": \"psup:7596\"}) pour chaque formation "
 "dont tu vas citer des chiffres, des conditions d'accès ou des débouchés : la fiche complète donne tous ses "
 "chiffres, sessions, sources et définitions. N'appelle pas l'outil si la question ne porte sur aucune formation.")
cas=[(cv,banc[cv]["turns"][0],"positif") for cv in d.SONDE]+[("V-INF-01",d.QUESTION_NEGATIVE,"negatif")]
def run(m):
    out=[]
    for conv,q,sens in cas:
        try: r=d.appel(c,m,S[conv][0].replace(PHRASE_OUTIL,PHRASE2),q,{"tool_choice":"auto"})
        except Exception as e: r={"erreur":str(e)[:200]}
        if r.get("modele_rendu") not in (None,m): r["erreur"]=f"modele rendu {r['modele_rendu']}"
        rec={**r,"variante":"phrase_explicite","reglages":{"tool_choice":"auto"},"conversation":conv,"sens":sens,"modele":m,"serveur":d.SERVEUR,"rep":1 if m=="mistral-medium-2604" else 0}
        open(f"results/banc_e/diag_outil/{m}.jsonl","a").write(json.dumps(rec,ensure_ascii=False)+"\n")
        out.append(f"{m} {conv} {sens} appels={len(r.get('appels',[]))} {r.get('appels')} fin={r.get('fin')} out={r.get('tokens_out')} {r.get('erreur','')}")
    return out
with ThreadPoolExecutor(4) as p:
    for o in p.map(run,["mistral-medium-2604","mistral-small-2603","zai-glm-5-2","zai-glm-5-3"]): print("\n".join(o),flush=True)
