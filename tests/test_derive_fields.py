"""Tests TDD — dérivation type_diplome + géocodage région (Phase 1a fill).

Ordre 2026-06-14-1230. Règle directrice : PRÉCISION > RAPPEL.
Une fiche mal typée est pire qu'une fiche vide -> on ne remplit que sur un
signal ancré certain (champ structuré fili_code Parcoursup, source monmaster,
departement->region appris du corpus). Sinon : VIDE.
"""
from src.collect.derive_fields import (
    derive_type_diplome,
    derive_rncp_professional_title,
    derive_lyceepro_insertion,
    derive_onisep_niveau,
    geocode_region,
    TYPE_FROM_FILI_CODE,
)


# --------------------------------------------------------------------------
# type_diplome
# --------------------------------------------------------------------------

def test_monmaster_devient_master():
    # MonMaster = portail master, 100 % bac+5 vérifié sur corpus.
    fiches = [{"source": "monmaster", "niveau": "bac+5", "type_diplome": None, "nom": "Acoustique"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] == "Master"


def test_monmaster_existant_non_ecrase():
    fiches = [{"source": "monmaster", "niveau": "bac+5", "type_diplome": "Master mention Droit"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] == "Master mention Droit"


def test_parcoursup_fili_bts():
    fiches = [{"source": "parcoursup", "fili_code": "BTS", "type_diplome": None, "nom": "BTS SIO"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] == "BTS"


def test_parcoursup_fili_but():
    fiches = [{"source": "parcoursup", "fili_code": "BUT", "type_diplome": None, "nom": "BUT Informatique"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] == "BUT"


def test_parcoursup_ecole_ingenieur_bac5_devient_diplome():
    # fili_code "Ecole d'Ingénieur" conflate le cycle prépa (bac+1-3) ET le cycle
    # ingénieur (bac+5). On ne type "Diplôme d'ingénieur" QUE le bac+5.
    fiches = [{"source": "parcoursup", "fili_code": "Ecole d'Ingénieur", "niveau": "bac+5",
               "type_diplome": None, "nom": "Formation d'ingénieur"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] == "Diplôme d'ingénieur"


def test_parcoursup_ecole_ingenieur_prepa_bac3_reste_vide():
    # Cycle préparatoire intégré (bac+3) = PAS encore le diplôme d'ingénieur -> vide.
    fiches = [{"source": "parcoursup", "fili_code": "Ecole d'Ingénieur", "niveau": "bac+3",
               "type_diplome": None, "nom": "Formation Bac + 3"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] is None


def test_parcoursup_ecole_ingenieur_niveau_inconnu_reste_vide():
    fiches = [{"source": "parcoursup", "fili_code": "Ecole d'Ingénieur", "niveau": None,
               "type_diplome": None, "nom": "Formation Bac + 3"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] is None


def test_parcoursup_fili_ifsi_devient_de_infirmier():
    # IFSI = institut de formation en soins infirmiers -> DE infirmier (sans ambiguïté).
    fiches = [{"source": "parcoursup", "fili_code": "IFSI", "type_diplome": None, "nom": "X"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] == "Diplôme d'État infirmier"


def test_parcoursup_fili_cpge():
    fiches = [{"source": "parcoursup", "fili_code": "CPGE", "type_diplome": None, "nom": "MPSI"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] == "CPGE"


def test_parcoursup_licence_simple():
    fiches = [{"source": "parcoursup", "fili_code": "Licence", "type_diplome": None, "nom": "Licence Droit"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] == "Licence"


def test_parcoursup_licence_las_reste_licence():
    # L.AS (Licence Accès Santé) = une licence.
    fiches = [{"source": "parcoursup", "fili_code": "Licence_Las", "type_diplome": None, "nom": "Licence SV - accès santé"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] == "Licence"


def test_parcoursup_licence_pro_raffine_depuis_intitule():
    # fili_code Licence + intitulé "professionnelle" -> raffinage ancré.
    fiches = [{"source": "parcoursup", "fili_code": "Licence", "type_diplome": None,
               "nom": "Licence professionnelle Métiers du BTP"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] == "Licence professionnelle"


def test_parcoursup_autre_formation_reste_vide():
    # "Autre formation" est ambigu -> jamais de devinette.
    fiches = [{"source": "parcoursup", "fili_code": "Autre formation", "type_diplome": None, "nom": "X"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] is None


def test_parcoursup_efts_reste_vide_conservateur():
    # EFTS -> DE travail social multiples (DEASS/DEES/DEEJE) : ambigu -> VIDE.
    fiches = [{"source": "parcoursup", "fili_code": "EFTS", "type_diplome": None, "nom": "X"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] is None


def test_parcoursup_fili_none_reste_vide():
    fiches = [{"source": "parcoursup", "fili_code": None, "type_diplome": None, "nom": "Architecture"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] is None


def test_parcoursup_existant_non_ecrase():
    fiches = [{"source": "parcoursup", "fili_code": "BTS", "type_diplome": "BTSA"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] == "BTSA"


def test_autre_source_hors_scope_non_touchee():
    # Priorité phase1a = parcoursup + monmaster. rncp/onisep intacts.
    fiches = [{"source": "rncp", "fili_code": "BTS", "type_diplome": None, "nom": "X"}]
    assert derive_type_diplome(fiches)[0]["type_diplome"] is None


def test_table_fili_code_couvre_les_codes_ancres():
    for code in ("BTS", "BUT", "Licence", "Licence_Las", "CPGE", "Ecole d'Ingénieur", "IFSI"):
        assert code in TYPE_FROM_FILI_CODE


# --------------------------------------------------------------------------
# rncp : certifs "sur demande" -> "Titre professionnel (RNCP)" (ordre 1305, Option A)
# --------------------------------------------------------------------------

def test_rncp_sur_demande_devient_titre_professionnel():
    # type_enregistrement = signal autoritaire (déterministe, 100% précis).
    fiches = [{"source": "rncp", "type_enregistrement": "Enregistrement sur demande",
               "type_diplome": None, "nom": "Acheteur"}]
    assert derive_rncp_professional_title(fiches)[0]["type_diplome"] == "Titre professionnel (RNCP)"


def test_rncp_de_droit_sans_type_reste_vide():
    # Les 37 certifs "de droit" dont l'abrégé n'a pas été capturé NE sont PAS des
    # titres pros : ce sont des diplômes formels -> rester vide, pas mal-étiqueter.
    fiches = [{"source": "rncp", "type_enregistrement": "Enregistrement de droit",
               "type_diplome": None, "nom": "X"}]
    assert derive_rncp_professional_title(fiches)[0]["type_diplome"] is None


def test_rncp_titre_pro_n_ecrase_pas_un_type_existant():
    fiches = [{"source": "rncp", "type_enregistrement": "Enregistrement sur demande",
               "type_diplome": "Master"}]
    assert derive_rncp_professional_title(fiches)[0]["type_diplome"] == "Master"


def test_rncp_sans_type_enregistrement_reste_vide():
    fiches = [{"source": "rncp", "type_diplome": None, "nom": "X"}]
    assert derive_rncp_professional_title(fiches)[0]["type_diplome"] is None


def test_titre_pro_ne_touche_pas_les_autres_sources():
    fiches = [{"source": "parcoursup", "type_enregistrement": "Enregistrement sur demande",
               "type_diplome": None}]
    assert derive_rncp_professional_title(fiches)[0]["type_diplome"] is None


# --------------------------------------------------------------------------
# lycée_pro : stats emploi top-level -> bloc insertion_pro (ordre 1327)
# --------------------------------------------------------------------------

def test_lyceepro_insertion_mappee():
    # stats fractions [0,1] -> noms de champs lus par fact_card.
    fiches = [{"source": "inserjeunes_lycee_pro", "taux_emploi_12m_moyen": 0.44,
               "taux_emploi_24m_moyen": 0.49, "taux_poursuite_etudes_moyen": 0.42}]
    ip = derive_lyceepro_insertion(fiches)[0]["insertion_pro"]
    assert ip["taux_emploi_12m"] == 0.44
    assert ip["taux_emploi_24m"] == 0.49
    assert ip["part_poursuite_etudes"] == 0.42
    assert ip["source"] == "inserjeunes_lycee_pro"


def test_lyceepro_insertion_existante_non_ecrasee():
    fiches = [{"source": "inserjeunes_lycee_pro", "insertion_pro": {"taux_emploi_12m": 0.9},
               "taux_emploi_12m_moyen": 0.44}]
    assert derive_lyceepro_insertion(fiches)[0]["insertion_pro"] == {"taux_emploi_12m": 0.9}


def test_lyceepro_sans_stat_pas_de_bloc():
    fiches = [{"source": "inserjeunes_lycee_pro", "libelle_formation": "X"}]
    out = derive_lyceepro_insertion(fiches)[0]
    assert not out.get("insertion_pro")


def test_lyceepro_partiel_ne_met_que_le_present():
    fiches = [{"source": "inserjeunes_lycee_pro", "taux_poursuite_etudes_moyen": 0.42}]
    ip = derive_lyceepro_insertion(fiches)[0]["insertion_pro"]
    assert ip["part_poursuite_etudes"] == 0.42
    assert "taux_emploi_12m" not in ip


def test_lyceepro_insertion_ne_touche_pas_autres_sources():
    fiches = [{"source": "parcoursup", "taux_emploi_12m_moyen": 0.44}]
    assert not derive_lyceepro_insertion(fiches)[0].get("insertion_pro")


# --------------------------------------------------------------------------
# onisep : niveau depuis niveau_certification (mapping empirique vérifié, ordre 1327)
# --------------------------------------------------------------------------

def test_onisep_niveau_depuis_certification_valeurs_sures():
    cas = {"1": "bac+5", "2": "bac+3", "3": "bac+2"}
    for nc, niv in cas.items():
        fiches = [{"source": "onisep", "niveau": None, "niveau_certification": nc}]
        assert derive_onisep_niveau(fiches)[0]["niveau"] == niv, f"nc={nc}"


def test_onisep_niveau_certif_ambigu_ou_insuffisant_reste_vide():
    # '0' ambigu (38% purity), '4' 3 ex, '5' 0 ex -> jamais mappé (précision > rappel).
    for nc in ("0", "4", "5"):
        fiches = [{"source": "onisep", "niveau": "", "niveau_certification": nc}]
        assert derive_onisep_niveau(fiches)[0]["niveau"] in ("", None), f"nc={nc}"


def test_onisep_niveau_existant_non_ecrase():
    fiches = [{"source": "onisep", "niveau": "bac+3", "niveau_certification": "1"}]
    assert derive_onisep_niveau(fiches)[0]["niveau"] == "bac+3"


def test_onisep_niveau_ne_touche_pas_autres_sources():
    fiches = [{"source": "rncp", "niveau": None, "niveau_certification": "1"}]
    assert derive_onisep_niveau(fiches)[0]["niveau"] is None


# --------------------------------------------------------------------------
# geocode_region
# --------------------------------------------------------------------------

def test_region_existante_non_ecrasee():
    fiches = [{"source": "parcoursup", "region": "Bretagne", "departement": "Rhône"}]
    assert geocode_region(fiches)[0]["region"] == "Bretagne"


def test_region_apprise_depuis_departement_du_corpus():
    # Un departement observé avec UNE région ailleurs -> appliqué aux vides (display exact).
    fiches = [
        {"source": "parcoursup", "departement": "Rhône", "region": "Auvergne-Rhône-Alpes", "ville": "Lyon"},
        {"source": "parcoursup", "departement": "Rhône", "region": "", "ville": ""},
    ]
    out = geocode_region(fiches)
    assert out[1]["region"] == "Auvergne-Rhône-Alpes"


def test_departement_ambigu_non_rempli():
    # Un departement observé avec 2 régions -> ambigu -> on ne remplit pas (conservateur).
    fiches = [
        {"source": "parcoursup", "departement": "Zone", "region": "RegA"},
        {"source": "parcoursup", "departement": "Zone", "region": "RegB"},
        {"source": "parcoursup", "departement": "Zone", "region": ""},
    ]
    assert geocode_region(fiches)[2]["region"] in ("", None)


def test_polynesie_via_supplement_overseas():
    # Departement COM "Polynésie française" non labellisé ailleurs -> supplément overseas.
    fiches = [{"source": "parcoursup", "departement": "Polynésie française", "region": "", "ville": "Papeete"}]
    assert geocode_region(fiches)[0]["region"] == "Polynésie française"


def test_etranger_reste_vide():
    fiches = [{"source": "parcoursup", "departement": "Etranger", "region": "", "ville": "Hanoï"}]
    assert geocode_region(fiches)[0]["region"] in ("", None)


def test_departement_absent_reste_vide():
    # Fiches nationales (rncp/onisep) sans departement -> JAMAIS de région fabriquée.
    fiches = [{"source": "rncp", "departement": None, "region": ""}]
    assert geocode_region(fiches)[0]["region"] in ("", None)
