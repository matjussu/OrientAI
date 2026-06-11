"""TDD garde-fou géo déterministe NARROW (J3, 2026-06-11).

Acceptance : Papeete-pour-Nantes DOIT couper (refus + relais).
Non-régression : intra-région (Grenoble/Annecy, Bordeaux, Montpellier) NE DOIT PAS couper.
Conservateur : doute de résolution -> abstention (pas de tir).
"""
from src.rag.geo_coherence import (
    geo_coherence_check,
    extract_target_zone,
)


def _f(ville=None, region=None, **kw):
    d = {"nom": kw.get("nom", "Formation"), "ville": ville, "region": region}
    d.update(kw)
    return d


# ---------- ACCEPTANCE : out-of-zone clair DOIT tirer ----------

def test_papeete_pour_nantes_tire():
    q = "Quel est le taux d'accès sur Parcoursup pour BTS Commerce international à Nantes ?"
    sources = [_f(ville="Papeete", region=None, nom="BTS Services Commerce International")]
    out = geo_coherence_check(q, sources)
    assert out is not None
    assert "Nantes" in out and "Parcoursup" in out


def test_papeete_region_none_resolue_par_table():
    # le coeur du fix : la fiche a region=None, la table résout Papeete -> Polynésie
    city, region = extract_target_zone("taux d'accès pour BTS à Nantes ?")
    assert region == "pays de la loire"
    assert geo_coherence_check("BTS à Nantes ?", [_f(ville="Papeete", region=None)]) is not None


def test_region_nommee_directement_hors_zone_tire():
    q = "Je cherche une licence en Bretagne, taux d'accès ?"
    sources = [_f(ville="Marseille", region="Provence-Alpes-Côte d'Azur")]
    assert geo_coherence_check(q, sources) is not None


# ---------- NON-RÉGRESSION : intra-région NE DOIT PAS tirer ----------

def test_grenoble_lyon_pour_annecy_ne_tire_pas():
    # Annecy + Grenoble/Lyon = même région Auvergne-Rhône-Alpes -> alternative cadrée OK
    q = "Quel est le taux d'accès sur Parcoursup pour licence MIASHS à Annecy ?"
    sources = [
        _f(ville="Grenoble", region="Auvergne-Rhône-Alpes"),
        _f(ville="Lyon", region="Auvergne-Rhône-Alpes"),
    ]
    assert geo_coherence_check(q, sources) is None


def test_bordeaux_intra_region_ne_tire_pas():
    # sources ville=None mais region=Nouvelle-Aquitaine = région de Bordeaux
    q = "Quel est le salaire médian à l'embauche après pour BUT TC à Bordeaux ?"
    sources = [_f(ville=None, region="Nouvelle-Aquitaine")]
    assert geo_coherence_check(q, sources) is None


def test_montpellier_intra_region_ne_tire_pas():
    q = "taux d'accès Parcoursup pour diplôme d'État infirmier à Montpellier ?"
    sources = [_f(ville=None, region="Occitanie")]
    assert geo_coherence_check(q, sources) is None


def test_meme_ville_exacte_ne_tire_pas():
    q = "prépa PCSI à Lille ?"
    sources = [_f(ville="Lille", region="Hauts-de-France")]
    assert geo_coherence_check(q, sources) is None


# ---------- CONSERVATEUR : doute -> abstention ----------

def test_sources_sans_geo_ne_tire_pas():
    # toutes les sources region=None ville=None -> pas de preuve out-of-zone -> abstention
    q = "salaire médian licence informatique à Rennes ?"
    sources = [_f(ville=None, region=None), _f(ville=None, region=None)]
    assert geo_coherence_check(q, sources) is None


def test_ville_inconnue_table_ne_tire_pas():
    q = "taux d'accès à Trifouillis-les-Oies ?"  # hors table
    sources = [_f(ville="Papeete", region=None)]
    assert geo_coherence_check(q, sources) is None


def test_ville_ambigue_ne_tire_pas():
    # Saint-Denis = homonyme (Réunion vs 93) -> jamais résolu -> abstention
    q = "licence à Saint-Denis ?"
    sources = [_f(ville="Papeete", region=None)]
    assert geo_coherence_check(q, sources) is None


def test_comparaison_multi_villes_ne_tire_pas():
    q = "compare l'INSA Lyon, l'UTC Compiègne et Polytech sur le taux d'accès"
    sources = [_f(ville="Lyon", region="Auvergne-Rhône-Alpes")]
    assert geo_coherence_check(q, sources) is None


def test_pas_de_contrainte_geo_ne_tire_pas():
    q = "Quelles sont les meilleures écoles d'ingénieurs en informatique ?"
    sources = [_f(ville="Papeete", region=None)]
    assert geo_coherence_check(q, sources) is None


def test_aucune_source_ne_tire_pas():
    # pas de source du tout -> pas de preuve out-of-zone -> abstention (le RAG gère)
    assert geo_coherence_check("BTS à Nantes ?", []) is None


def test_source_wrapper_retrieval_papeete_tire():
    # forme LIVE du pipeline : wrapper {_sub_index, score, fiche:{...}} (pas aplati)
    q = "Quel est le taux d'accès pour BTS Commerce international à Nantes ?"
    wrapped = [{
        "_sub_index": "formations", "score": 0.7,
        "fiche": {"nom": "BTS Services Commerce International",
                  "ville": "Papeete", "region": None,
                  "departement": "Polynésie française"},
    }]
    out = geo_coherence_check(q, wrapped)
    assert out is not None and "Nantes" in out


def test_source_wrapper_intra_region_ne_tire_pas():
    # wrapper live, source intra-région (Grenoble pour Annecy) -> abstention
    q = "licence MIASHS à Annecy ?"
    wrapped = [{"_sub_index": "formations", "score": 0.7,
                "fiche": {"ville": "Grenoble", "region": "Auvergne-Rhône-Alpes"}}]
    assert geo_coherence_check(q, wrapped) is None


# ---------- extraction ----------

def test_extract_zone_ville_simple():
    assert extract_target_zone("licence à Lyon ?") == ("lyon", "auvergne rhone alpes")


def test_extract_zone_aucune():
    assert extract_target_zone("c'est quoi une licence ?") == (None, None)


def test_extract_zone_multi_villes_abstention():
    assert extract_target_zone("compare Lyon et Lille") == (None, None)
