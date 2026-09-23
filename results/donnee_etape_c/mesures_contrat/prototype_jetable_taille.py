# PROTOTYPE JETABLE, garde comme trace des chiffres cites par CONTRACT.md section 3. Chemins de la machine de Claudette ; duckdb installe hors depot.
# PROTOTYPE JETABLE (ordre 2026-09-23-1358) : taille d'une base "une ligne par chiffre" et de son export.
import json, sqlite3, os, gzip, time, sys
SP=sys.argv[1]
d=json.load(open("data/processed/formations_etape_b2.json"))
T={"informatique","cyber","data_ia","sante"}
dans=lambda f: f["source"] in ("parcoursup","parcoursup_apprentissage") and (f.get("domaine") in T or (f.get("domaine")=="sciences_fondamentales" and f.get("domaine_regle") in ("M01","M02","M03")))
p=[f for f in d if dans(f)]
def plat(x, pre=""):
    if isinstance(x, dict):
        for k,v in x.items(): yield from plat(v, f"{pre}.{k}" if pre else k)
    elif isinstance(x,(int,float)) and not isinstance(x,bool): yield pre, x
vals=[]
for f in p:
    fid=f["source"]+":"+f["cod_aff_form"]
    for bloc in ("admission","profil_admis","cout","insertion","sante","apprentissage"):
        for k,v in plat(f.get(bloc) or {}, bloc):
            vals.append((fid,k,v,1,"session 2025"))
print("fiches",len(p),"valeurs numeriques",len(vals))
db=SP+"/t.sqlite"; os.path.exists(db) and os.remove(db)
s=sqlite3.connect(db); s.execute("create table valeur(id text,champ text,v real,source integer,millesime text)")
s.executemany("insert into valeur values (?,?,?,?,?)",vals); s.execute("create index i on valeur(id)"); s.commit(); s.execute("vacuum"); s.close()
print("sqlite Mo",round(os.path.getsize(db)/1e6,1))
exp={}
for fid,k,v,src,m in vals: exp.setdefault(fid,{})[k]=[v,src]
js=json.dumps(exp,ensure_ascii=False,separators=(",",":")).encode()
print("export json Mo",round(len(js)/1e6,2),"gz Mo",round(len(gzip.compress(js))/1e6,2))
t=time.perf_counter(); json.loads(js); print("parse ms",round((time.perf_counter()-t)*1000))
