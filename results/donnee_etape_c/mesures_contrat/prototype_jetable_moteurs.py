# PROTOTYPE JETABLE, garde comme trace des chiffres cites par CONTRACT.md section 3. Chemins de la machine de Claudette ; duckdb installe hors depot.
# PROTOTYPE JETABLE de mesure (ordre 2026-09-23-1358) : ne construit pas la base, mesure les moteurs.
import json, csv, re, sys, time, sqlite3, math, gzip, os
sys.path.insert(0, sys.argv[1]+"/duck"); import duckdb
SP=sys.argv[1]
d=json.load(open("data/processed/formations_etape_b2.json"))
ex=json.load(open("/home/matteo_linux/projets/_orientai-ref/verticale-2026-09/explorateur/data_b2.json"))
dom={r["id"]+"|"+r["src"]:r["dom"] for r in ex["fiches"]}
gps={}
for r in csv.DictReader(open("../OrientIA/data/raw/cartographie_parcoursup_2025.csv",encoding="utf-8-sig"),delimiter=";"):
    if r["etab_gps"]:
        la,lo=[float(x) for x in r["etab_gps"].split(",")]
        for g in r["gta"].split(","): gps[g.strip()]=(la,lo)
rows=[]; prov=[]
for f in d:
    k=str(f.get("cod_aff_form"))+"|"+f["source"]
    if k not in dom: continue
    pid=("psup:" if f["source"]=="parcoursup" else "psup_app:")+k.split("|")[0]
    la,lo=gps.get(f["cod_aff_form"],(None,None))
    adm=f.get("admission") or {}; h=adm.get("historique") or {}
    rows.append((pid,f["nom"],f["etablissement"],f.get("fili_code"),f.get("type_formation"),f.get("statut"),f.get("code_insee"),f.get("code_departement"),f.get("region"),la,lo,
      f.get("taux_acces_parcoursup_2025"),f.get("nombre_places"),(adm.get("volumes") or {}).get("voeux_totaux"),
      (h.get("2024") or {}).get("taux_acces"),(h.get("2023") or {}).get("taux_acces"),
      ",".join(dom[k]), f.get("selectivite_code")))
    for champ in ("taux_acces","places","voeux","cout","alternance","insertion"):
        prov.append((pid,champ,"parcoursup_2025","session 2025","https://data.enseignementsup-recherche.gouv.fr/...",f.get("lien_form_psup")))
print("lignes",len(rows),"prov",len(prov))
cols="id,nom,etab,fili,type,statut,insee,dep,region,lat,lon,taux,places,voeux,taux_2024,taux_2023,domaines,selectivite"
for p in (SP+"/p.sqlite",SP+"/p.duckdb"):
    if os.path.exists(p): os.remove(p)
s=sqlite3.connect(SP+"/p.sqlite"); s.execute(f"create table f({cols})"); s.executemany(f"insert into f values ({','.join('?'*18)})",rows)
s.execute("create table prov(id,champ,source,millesime,url,url_fiche)"); s.executemany("insert into prov values (?,?,?,?,?,?)",prov); s.commit()
s.create_function("hav",4,lambda a,b,c,e: None if a is None else 2*6371*math.asin(math.sqrt(math.sin(math.radians(c-a)/2)**2+math.cos(math.radians(a))*math.cos(math.radians(c))*math.sin(math.radians(e-b)/2)**2)))
q="select id,nom,etab,taux,round(hav(lat,lon,48.1159,-1.6884),1) km from f where fili='BUT' and domaines like '%informatique%' and taux>50 and hav(lat,lon,48.1159,-1.6884)<50 order by km"
t=time.perf_counter()
for _ in range(100): r=s.execute(q).fetchall()
print("sqlite ms/req",round((time.perf_counter()-t)*10,3)); [print(x) for x in r]
s.close()
dk=duckdb.connect(SP+"/p.duckdb"); dk.execute(f"create table f(id varchar,nom varchar,etab varchar,fili varchar,type varchar,statut varchar,insee varchar,dep varchar,region varchar,lat double,lon double,taux double,places integer,voeux integer,taux_2024 double,taux_2023 double,domaines varchar,selectivite varchar)")
dk.executemany(f"insert into f values ({','.join('?'*18)})",rows)
dk.execute("create table prov(id varchar,champ varchar,source varchar,millesime varchar,url varchar,url_fiche varchar)"); dk.executemany("insert into prov values (?,?,?,?,?,?)",prov)
qd="select id,nom,taux, 2*6371*asin(sqrt(pow(sin(radians(48.1159-lat)/2),2)+cos(radians(lat))*cos(radians(48.1159))*pow(sin(radians(-1.6884-lon)/2),2))) km from f where fili='BUT' and domaines like '%informatique%' and taux>50 and km<50 order by km"
t=time.perf_counter()
for _ in range(100): r2=dk.execute(qd).fetchall()
print("duckdb ms/req",round((time.perf_counter()-t)*10,3), len(r2)); dk.close()
print("taille sqlite Ko",os.path.getsize(SP+"/p.sqlite")//1024,"duckdb Ko",os.path.getsize(SP+"/p.duckdb")//1024)
js=json.dumps({"cols":cols.split(","),"rows":rows},ensure_ascii=False).encode()
print("export json Ko",len(js)//1024,"gz Ko",len(gzip.compress(js))//1024)
print("sans gps parmi 3 domaines", sum(1 for x in rows if x[9] is None), [x[0] for x in rows if x[9] is None][:10])
print("sans insee", sum(1 for x in rows if not x[6]))
