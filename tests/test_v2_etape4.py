"""Cerveau v2, étape 4 (CONTRAT-etape4, sections 6, 7 et 14) : outils (T1 à T4), vérificateur (libellé, absence),
boucle (B1, réécriture), prompt v1 figé, raisonnement, définitions de la base (D4).

Chaque garantie a son test de sabotage (règle 9, levier ORIENTIA_SABOTAGE_V2, ou injection de dépendance) : la
vérification qui la protège doit rougir quand on la casse. Aucun test ne charge le .env ni n'appelle d'API. Les tests
qui lisent la base C sont sautés quand elle n'est pas construite (CI).
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.base_c import outils as bc
from src.v2 import prompt as prompts
from src.v2 import verificateur as vf
from src.v2.outils import PERIMETRE_VIDE, Outils, Resultat
from src.v2.pipeline import MESSAGE_FIN, EtatConversation, Pipeline

VRAIE_BASE = Path(bc.BASE_DEFAUT)
base_requise = pytest.mark.skipif(not VRAIE_BASE.exists(), reason="base de l'étape C non construite")
RACINE = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def outils():
    if not VRAIE_BASE.exists():
        pytest.skip("base de l'étape C non construite")
    return Outils()


# ── T1 : sigles et mots entiers ────────────────────────────────────────────────────────────
@base_requise
def test_filiere_sigle_depliee(outils):
    """V-INF-03 (étape 3) : « CIEL » était refusé (valeurs proches FCIL, PCSI) ; 5 BTS CIEL existent à Rennes et Bruz."""
    r = outils.executer("chercher_formations", {"types": ["bts"], "filieres": ["CIEL"],
                                                "pres_de": {"commune": "Rennes", "rayon_km": 30}})
    assert r.erreur is None and "psup:17725" in r.ids and r.meta["filieres_depliees"]["CIEL"]


def _intitule_par_mots(outils) -> bool:
    r = outils.executer("chercher_formations", {"types": ["bts"], "intitule_contient": "CIEL"})
    textes = [outils.par_id[i]["intitule_norm"] for i in r.ids]
    return bool(textes) and all("cybersecurite" in t for t in textes) and not any("distanciel" in t for t in textes)


@base_requise
def test_intitule_par_mots_pas_de_distanciel(outils):
    assert _intitule_par_mots(outils)


@base_requise
def test_sabotage_intitule_sous_chaine_fait_rougir(outils, monkeypatch):
    monkeypatch.setenv("ORIENTIA_SABOTAGE_V2", "intitule_sous_chaine")
    assert not _intitule_par_mots(outils)


@base_requise
def test_intitule_debut_de_mot_garde_les_prefixes(outils):
    r = outils.executer("chercher_formations", {"intitule_contient": "électroradiologie",
                                                "pres_de": {"commune": "Lyon", "rayon_km": 100}})
    assert r.erreur is None and r.meta["nb_resultats"] >= 1


# ── T2 et T3 : trouver_formation ───────────────────────────────────────────────────────────
@base_requise
def test_ex_aequo_caches_signales_et_options_montrees(outils):
    """V-SAN-02 (étape 3) : 13 PASS de Lille à score égal, 10 montrés sans leur option, psup:36433 (6 %) caché."""
    r = outils.executer("trouver_formation", {"texte": "PASS", "commune": "Lille", "types": ["pass"]})
    assert r.meta["ex_aequo_caches"] == 3 and "non montrés" in r.texte
    assert "(option" in r.texte


@base_requise
def test_resultat_vide_dit_le_perimetre(outils):
    r = outils.executer("chercher_formations", {"types": ["but"], "apprentissage": True,
                                                "pres_de": {"commune": "Lille", "rayon_km": 20}})
    assert r.meta["nb_resultats"] == 0 and PERIMETRE_VIDE in r.texte


# ── T4 : une définition par notion ─────────────────────────────────────────────────────────
def _definitions_une_fois(outils) -> bool:
    r = outils.executer("lire_fiche", {"ids": ["psup:7596", "psup:7520"]})
    notions = [l.split(" : ", 1)[0] for l in r.texte.splitlines() if l.startswith("- ") and "Définition :" in l]
    return bool(notions) and len(notions) == len(set(notions)) and r.texte.count("Définition :") == len(notions)


@base_requise
def test_lire_fiche_plusieurs_ids_une_definition_par_notion(outils):
    assert _definitions_une_fois(outils)
    un = outils.executer("lire_fiche", {"ids": ["psup:7596"]})
    assert un.texte.count("Définition :") >= 5     # une fiche seule garde toutes ses définitions


@base_requise
def test_sabotage_definitions_supprimees_fait_rougir(outils, monkeypatch):
    monkeypatch.setenv("ORIENTIA_SABOTAGE_V2", "definitions_supprimees")
    assert not _definitions_une_fois(outils)


# ── 6.1 : libellé ─────────────────────────────────────────────────────────────────────────
PORTEURS = [
    {"valeur": 47.5, "unite": "pct", "id": "psup:1", "cle": "passage_mmopk_1_ou_2_ans_national@2024", "source_id": "s",
     "portee": "nationale", "libelle": "Passage en MMOPK en 1 ou 2 ans"},
    {"valeur": 3950.0, "unite": "eur", "id": "psup:2", "cle": "cout.scolarite_total_eur", "source_id": "s",
     "portee": "formation", "libelle": "Frais de scolarité du cycle"},
    {"valeur": 34.0, "unite": "pct", "id": "psup:3", "cle": "taux_acces@2025", "source_id": "s",
     "portee": "formation", "libelle": "Taux d'accès"},
]


def _libelles_attrapes() -> bool:
    t = ("Le passage en MMOPK est de 47,5 %. Les frais sont de 3 950 €/an. Le taux d'accès est de 34 %.")
    v = vf.verifier(t, PORTEURS)
    fautes = {c["valeur"] for c in vf.mal_nommes(t, v["adosses"], PORTEURS)}
    juste = "Au niveau national, le passage en MMOPK est de 47,5 %. Les frais du cycle sont de 3 950 €."
    vj = vf.verifier(juste, PORTEURS)
    return fautes == {47.5, 3950.0} and not vf.mal_nommes(juste, vj["adosses"], PORTEURS)


def test_verificateur_libelle_portee_et_periode():
    assert _libelles_attrapes()


def test_sabotage_libelle_laisse_passer_fait_rougir(monkeypatch):
    monkeypatch.setenv("ORIENTIA_SABOTAGE_V2", "libelle_laisse_passer")
    assert not _libelles_attrapes()


def test_libelle_dans_un_tableau_lit_l_en_tete():
    t = "| Voie | Passage national en MMOPK |\n|---|---|\n| PASS | 47,5 % |"
    v = vf.verifier(t, PORTEURS)
    assert v["adosses"] and not vf.mal_nommes(t, v["adosses"], PORTEURS)


# ── 6.2 : absence ─────────────────────────────────────────────────────────────────────────
OUTILS_TRONQUES = [{"nom": "trouver_formation", "execute": True, "erreur": None,
                    "meta": {"tronque": True, "nb_candidats": 13}}]


def _absence_attrapee() -> bool:
    t = "Pas de panique. Aucune option du PASS de Lille n'est à 6 %. Voici les chiffres."
    return vf.absences(t) == ["Aucune option du PASS de Lille n'est à 6 %."] and bool(vf.motif_incomplet(OUTILS_TRONQUES))


def test_absence_detectee_quand_le_resultat_est_tronque():
    assert _absence_attrapee()
    assert vf.motif_incomplet([{"nom": "lire_fiche", "execute": True, "erreur": None, "meta": {}}]) is None
    assert not vf.absences("Ce chiffre n'est pas publié pour cette formation. Aucun chiffre n'est disponible.")


def test_sabotage_absence_laisse_passer_fait_rougir(monkeypatch):
    monkeypatch.setenv("ORIENTIA_SABOTAGE_V2", "absence_laisse_passer")
    assert not _absence_attrapee()


# ── Boucle : doublures ────────────────────────────────────────────────────────────────────
def _msg(texte="", appels=()):
    calls = [SimpleNamespace(id=f"c{i}", function=SimpleNamespace(name=n, arguments=json.dumps(a)))
             for i, (n, a) in enumerate(appels)]
    return SimpleNamespace(model="zai-glm-5-3", choices=[SimpleNamespace(
        message=SimpleNamespace(content=texte, tool_calls=calls or None), finish_reason="stop")])


class ModeleFaux:
    def __init__(self, reponses):
        self.reponses, self.recus = list(reponses), []
        self.chat = self

    def complete(self, **kw):
        self.recus.append(json.loads(json.dumps(kw, default=str)))
        return self.reponses.pop(0)


VALEURS = [{"valeur": 34.0, "unite": "pct", "id": "psup:7596", "cle": "taux_acces@2025", "source_id": "s",
            "portee": "formation", "libelle": "Taux d'accès"}]


class OutilsFaux:
    index: list = []

    def __init__(self, meta=None):
        self.executes, self.meta = [], meta or {}

    def executer(self, nom, arguments, etat=None):
        self.executes.append(nom)
        return Resultat(texte="[psup:7596] taux d'accès 34 %", ids=["psup:7596"], valeurs=list(VALEURS),
                        meta=dict(self.meta))


class FiltreFaux:
    def classify(self, message, history=None):
        return SimpleNamespace(label="in_scope", via="faux", reason="test", pre_written_response=None)


def _pipeline(reponses, meta=None, **kw):
    modele, outils = ModeleFaux(reponses), OutilsFaux(meta)
    return Pipeline(modele, outils=outils, classifieur=FiltreFaux(), sommeil=lambda s: None, **kw), modele, outils


def _fin_annoncee() -> bool:
    six = [("lire_fiche", {"id": f"psup:{i}"}) for i in range(6)]
    p, modele, outils = _pipeline([_msg(appels=six), _msg("Le taux d'accès est de 34 %.")])
    r = p.repondre("question", EtatConversation())
    dernier = modele.recus[-1]
    return (len(outils.executes) == 6 and "tools" not in dernier
            and dernier["messages"][-1] == {"role": "user", "content": MESSAGE_FIN} and bool(r["trace"].get("fin_annoncee")))


def test_sixieme_outil_pile_le_modele_est_prevenu():
    assert _fin_annoncee()


def test_sabotage_fin_non_annoncee_fait_rougir(monkeypatch):
    monkeypatch.setenv("ORIENTIA_SABOTAGE_V2", "fin_non_annoncee")
    assert not _fin_annoncee()


def test_reecriture_absence_puis_trace_sans_retrait():
    """D5 = b (précision 75 % au lot 0) : l'absence déclenche une réécriture ; gardée, elle est tracée, pas retirée."""
    p, modele, _ = _pipeline([
        _msg(appels=[("trouver_formation", {"texte": "PASS"})]),
        _msg("Le taux d'accès est de 34 %. Aucune option du PASS ne descend aussi bas."),
        _msg("Le taux d'accès est de 34 %. Aucune option du PASS ne descend aussi bas."),
    ], meta={"tronque": True, "nb_candidats": 13})
    r = p.repondre("question", EtatConversation())
    consigne = modele.recus[2]["messages"][-1]["content"]
    assert "Tu affirmes une absence" in consigne and "ne la mentionne pas" in consigne
    assert r["trace"]["absences_gardees"] == ["Aucune option du PASS ne descend aussi bas."]
    assert "Aucune option" in r["reponse"] and r["trace"]["phrases_retirees"] == []


def test_libelle_faux_garde_apres_reecriture_est_retire():
    valeurs_nat = [{"valeur": 47.5, "unite": "pct", "id": "psup:1", "cle": "passage_mmopk_1_ou_2_ans_national@2024",
                    "source_id": "s", "portee": "nationale", "libelle": "Passage en MMOPK en 1 ou 2 ans"}]

    class OutilsNat(OutilsFaux):
        def executer(self, nom, arguments, etat=None):
            return Resultat(texte="passage national 47,5 %", ids=["psup:1"], valeurs=list(valeurs_nat))

    modele = ModeleFaux([_msg(appels=[("lire_fiche", {"id": "psup:1"})]),
                         _msg("Bonne question. Le passage en MMOPK est de 47,5 %."),
                         _msg("Bonne question. Le passage en MMOPK est de 47,5 %.")])
    p = Pipeline(modele, outils=OutilsNat(), classifieur=FiltreFaux(), sommeil=lambda s: None)
    r = p.repondre("question", EtatConversation())
    assert "mal nommés" in modele.recus[2]["messages"][-1]["content"]
    assert r["reponse"] == "Bonne question." and r["trace"]["phrases_retirees"] == ["Le passage en MMOPK est de 47,5 %."]


def test_reasoning_effort_envoye_seulement_si_demande():
    p, modele, _ = _pipeline([_msg("Bonjour.")], reasoning_effort="none")
    p.repondre("question", EtatConversation())
    assert modele.recus[0]["reasoning_effort"] == "none"
    p, modele, _ = _pipeline([_msg("Bonjour.")])
    p.repondre("question", EtatConversation())
    assert "reasoning_effort" not in modele.recus[0]


def test_pipeline_joue_le_prompt_v1_par_defaut():
    p, modele, _ = _pipeline([_msg("Bonjour.")])
    p.repondre("question", EtatConversation())
    assert modele.recus[0]["messages"][0]["content"].startswith(prompts.TEXTES["v1"])
    assert "Quand tu ne trouves pas" in prompts.TEXTES["v1"]


# ── Prompt v1 figé ────────────────────────────────────────────────────────────────────────
def test_prompt_v1_est_celui_valide_par_matteo():
    assert prompts.SHAS_FICHIER["v1"] == prompts.VALIDES["v1"]


def test_prompt_modifie_refuse_de_se_charger(tmp_path, monkeypatch):
    faux = tmp_path / "v1.txt"
    faux.write_bytes(prompts.CHEMINS["v1"].read_bytes() + b" ")
    monkeypatch.setitem(prompts.CHEMINS, "v1", faux)
    with pytest.raises(prompts.PromptModifie):
        prompts._lire("v1")


# ── D4 : définitions de la base ───────────────────────────────────────────────────────────
TABLE_CHAMPS = RACINE / "data/reference/champs_etape_c.csv"


def _lignes_mal_formees(texte: str) -> list[str]:
    lignes = list(csv.reader(io.StringIO(texte), delimiter=";"))
    return [l[0] for l in lignes[1:] if l and len(l) != len(lignes[0])]


def test_table_des_champs_bien_formee():
    """Un « ; » dans une définition décale les colonnes sans erreur (constaté le 26/09 en corrigeant D4 :
    `montre_au_modele` des parts d'accès était devenu du texte, 3 chiffres disparus de la fiche)."""
    texte = TABLE_CHAMPS.read_text(encoding="utf-8")
    assert _lignes_mal_formees(texte) == []
    sabotee = texte.replace("Le niveau réel en maths.", "Le niveau ; réel en maths.", 1)
    assert sabotee != texte
    assert _lignes_mal_formees(sabotee), "le contrôle doit voir une ligne décalée"


@base_requise
def test_definitions_de_repartition():
    from src.eval.controle_definitions import repartitions_mal_definies
    con = bc.Base.ouvrir().con
    assert repartitions_mal_definies(con) == []
    ancienne = ("Libellé officiel : part des terminales de cette série qui étaient en position de recevoir une "
                "proposition en phase principale.")
    fautes = repartitions_mal_definies(con, {c: ancienne for c in ("part_acces_general", "part_acces_techno",
                                                                   "part_acces_pro")})
    assert {f["champ"] for f in fautes} == {"part_acces_general", "part_acces_techno", "part_acces_pro"}
