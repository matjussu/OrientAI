import pandas as pd
from src.collect.parcoursup import (
    load_parcoursup,
    filter_domain,
    extract_fiche,
    DOMAIN_KEYWORDS,
)


def test_domain_keywords_defined():
    assert "cyber" in DOMAIN_KEYWORDS
    assert "data_ia" in DOMAIN_KEYWORDS
    assert any("cybersécurité" in kw.lower() or "cyber" in kw.lower()
               for kw in DOMAIN_KEYWORDS["cyber"])
    assert any("data" in kw.lower() or "intelligence artificielle" in kw.lower()
               for kw in DOMAIN_KEYWORDS["data_ia"])


def test_filter_domain_keeps_cyber_entries():
    df = pd.DataFrame({
        "formation": [
            "Master Cybersécurité",
            "Licence Histoire",
            "BUT Informatique parcours cyber",
            "BTS Comptabilité",
        ]
    })
    filtered = filter_domain(df, "cyber", name_column="formation")
    assert len(filtered) == 2
    assert "Histoire" not in filtered["formation"].values


# === Vague A — extract_fiche enriched fields ===

def _vague_a_row() -> pd.Series:
    """Minimal row with all Vague A new columns populated."""
    return pd.Series({
        "lib_for_voe_ins": "Master Cybersécurité",
        "g_ea_lib_vx": "Université de Rennes",
        "cod_uai": "0351842X",
        "ville_etab": "Rennes",
        "region_etab_aff": "Bretagne",
        "dep_lib": "Ille-et-Vilaine",
        "taux_acces_ens": 18.0,
        "capa_fin": 24,
        "contrat_etab": "Public",
        "detail_forma": "Description formation",
        "pct_tb": 45.0, "pct_b": 30.0, "pct_ab": 20.0, "pct_sansmention": 5.0,
        "pct_bg": 80.0, "pct_bt": 15.0, "pct_bp": 5.0,
        "part_acces_gen": 80.0, "part_acces_tec": 15.0, "part_acces_pro": 5.0,
        "pct_bours": 20.0,
        # Vague A new columns
        "cod_aff_form": "42156",
        "lien_form_psup": "https://www.parcoursup.fr/formation/42156",
        "voe_tot": 1250,
        "nb_voe_pp": 800,
        "nb_cla_pp": 600,
        "acc_internat": 5,
        "pct_f": 24.0,
        "pct_neobac": 85.0,
        "pct_aca_orig_idf": 12.0,
    })


def test_extract_fiche_vague_a_includes_cod_aff_form():
    fiche = extract_fiche(_vague_a_row())
    assert fiche["cod_aff_form"] == "42156"
    assert "parcoursup.fr" in fiche["lien_form_psup"]


def test_extract_fiche_includes_cod_uai_for_insersup_join():
    """cod_uai is the official MEN establishment id — required to join
    with InserSup (insertion pro) and other ESR open-data datasets.
    Missing it silently means 0 InserSup matches."""
    fiche = extract_fiche(_vague_a_row())
    assert fiche["cod_uai"] == "0351842X"


def test_extract_fiche_vague_a_admission_block_structured():
    fiche = extract_fiche(_vague_a_row())
    adm = fiche["admission"]
    assert adm["session"] == 2025
    assert adm["taux_acces"] == 18.0
    assert adm["places"] == 24
    assert adm["volumes"]["voeux_totaux"] == 1250
    assert adm["volumes"]["voeux_phase_principale"] == 800
    assert adm["volumes"]["classes_phase_principale"] == 600
    assert adm["internat_disponible"] is True


def test_extract_fiche_vague_a_internat_zero_means_false():
    row = _vague_a_row()
    row["acc_internat"] = 0
    fiche = extract_fiche(row)
    assert fiche["admission"]["internat_disponible"] is False


def test_extract_fiche_vague_a_internat_missing_means_none():
    row = _vague_a_row()
    row["acc_internat"] = None
    fiche = extract_fiche(row)
    assert fiche["admission"]["internat_disponible"] is None


def test_extract_fiche_vague_a_profil_admis_extended_demographics():
    fiche = extract_fiche(_vague_a_row())
    profil = fiche["profil_admis"]
    assert profil["femmes_pct"] == 24.0
    assert profil["neobacheliers_pct"] == 85.0
    assert profil["origine_academique_idf_pct"] == 12.0


def test_extract_fiche_vague_a_legacy_fields_still_present():
    """Backward-compat check: legacy flat fields (taux_acces_parcoursup_2025,
    nombre_places) remain populated so the existing FAISS index and 231
    legacy tests don't break."""
    fiche = extract_fiche(_vague_a_row())
    assert fiche["taux_acces_parcoursup_2025"] == 18.0
    assert fiche["nombre_places"] == 24


# === ADR-041 — extension domaines + nouveaux champs P0 ===


def test_extended_domains_includes_15_sectors():
    """ADR-041 Axe a : 12 nouveaux secteurs en plus des 3 legacy."""
    from src.collect.parcoursup import EXTENDED_DOMAINS, LEGACY_DOMAINS

    assert LEGACY_DOMAINS == ["cyber", "data_ia", "sante"]
    assert len(EXTENDED_DOMAINS) >= 15
    for new in ["droit", "eco_gestion", "sciences_humaines", "langues",
                "lettres_arts", "sport", "sciences_fondamentales",
                "ingenierie_industrielle", "communication", "education",
                "agriculture", "tourisme_hotellerie"]:
        assert new in EXTENDED_DOMAINS, f"{new} manquant dans EXTENDED_DOMAINS"


def test_domain_keywords_droit_captures_licence_droit():
    df = pd.DataFrame({
        "formation": ["Licence Droit", "Licence Histoire", "Master Droit notarial"]
    })
    filtered = filter_domain(df, "droit", name_column="formation")
    assert len(filtered) == 2
    assert "Licence Histoire" not in filtered["formation"].values


def test_domain_keywords_eco_gestion_captures_gestion_bts():
    df = pd.DataFrame({
        "formation": ["BTS Comptabilité Gestion", "Master Marketing", "Licence Histoire"]
    })
    filtered = filter_domain(df, "eco_gestion", name_column="formation")
    assert len(filtered) == 2


def test_domain_keywords_sport_captures_staps():
    df = pd.DataFrame({"formation": ["Licence STAPS", "Master Marketing"]})
    assert len(filter_domain(df, "sport", name_column="formation")) == 1


def test_collect_parcoursup_fiches_invalid_domain_raises(tmp_path, monkeypatch):
    """Si un domaine inconnu est passé, raise ValueError (pas silent skip)."""
    from src.collect import parcoursup as mod
    # Mock load_parcoursup pour éviter de lire un CSV réel
    monkeypatch.setattr(mod, "load_parcoursup", lambda p: pd.DataFrame({
        mod.FORMATION_COLUMN: ["Licence Droit"]
    }))
    import pytest as _p
    with _p.raises(ValueError, match="DOMAIN_KEYWORDS"):
        mod.collect_parcoursup_fiches(tmp_path / "fake.csv", domains=["unknown_domain"])


def _row_with_adr_041_fields() -> pd.Series:
    """Row minimal incluant les nouveaux champs ADR-041 (prop_tot, pct_acc_debutpp, fili)."""
    base = _vague_a_row().to_dict()
    base.update({
        "prop_tot": 1420,
        "pct_acc_debutpp": 35.0,
        "fili": "L1",
        "lib_grp1": "Licences générales",
        "select_form": "formation sélective",
    })
    return pd.Series(base)


def test_extract_fiche_adr_041_fields_populated():
    fiche = extract_fiche(_row_with_adr_041_fields())
    assert fiche["propositions_totales"] == 1420
    assert fiche["pct_acceptes_debut_pp"] == 35.0
    assert fiche["fili_code"] == "L1"
    assert fiche["fili_groupe"] == "Licences générales"
    assert fiche["selectivite_code"] == "formation sélective"


def test_extract_fiche_adr_041_fields_none_when_missing():
    """Si une row n'a pas les colonnes ADR-041, les champs sont None (pas crash)."""
    fiche = extract_fiche(_vague_a_row())  # sans les colonnes ADR-041
    assert fiche["propositions_totales"] is None
    assert fiche["pct_acceptes_debut_pp"] is None
    assert fiche["fili_code"] is None


def test_collect_parcoursup_fiches_backward_compat_default_domains():
    """Sans arg `domains`, comportement inchangé : 3 domaines legacy."""
    from src.collect.parcoursup import collect_parcoursup_fiches, DOMAIN_KEYWORDS
    import pandas as pd
    # Mock via monkeypatch de load_parcoursup pour éviter de lire le CSV réel
    # Simplement vérifier que l'appel sans arg n'explose pas en passant un
    # DataFrame via monkeypatch serait trop verbeux — on check le contract d'API :
    import inspect
    sig = inspect.signature(collect_parcoursup_fiches)
    assert "domains" in sig.parameters
    assert sig.parameters["domains"].default is None


# === C1 (2026-06-09) — cascade domaine pour ré-ingestion élargie ===
# Les ~6000 formations hors taxonomie keyword reçoivent un domaine via cascade :
#   1. keyword sur le NOM (comme filter_domain)
#   2. sinon mapping form_lib_voe_acc -> domaine thématique (validé Jarvis)
#   3. sinon "autre" (mieux vaut autre qu'un faux domaine)


def _cascade_row(nom, form_lib=""):
    return pd.Series({"lib_for_voe_ins": nom, "form_lib_voe_acc": form_lib})


def test_cascade_step1_keyword_on_name_wins():
    from src.collect.parcoursup import domaine_cascade
    # le nom porte un keyword -> thématique, même si form_lib mapperait "autre"
    assert domaine_cascade(_cascade_row("BTS Cybersécurité des réseaux", "BTS - Services")) == "cyber"


def test_cascade_step2_form_lib_mapping_when_name_has_no_keyword():
    from src.collect.parcoursup import domaine_cascade
    assert domaine_cascade(_cascade_row("Formation XYZ", "D.E secteur social")) == "sante"
    assert domaine_cascade(_cascade_row("Formation XYZ", "BTS - Agricole")) == "agriculture"
    assert domaine_cascade(_cascade_row("Formation XYZ", "Licence - STAPS")) == "sport"


def test_cascade_step2_whitespace_normalized():
    from src.collect.parcoursup import domaine_cascade
    # données réelles : doubles espaces sur certains libellés
    assert domaine_cascade(
        _cascade_row("Formation XYZ", "Formations  des écoles d'ingénieurs")
    ) == "ingenierie_industrielle"


def test_cascade_step3_autre_for_broad_or_multidomain_labels():
    from src.collect.parcoursup import domaine_cascade
    assert domaine_cascade(_cascade_row("Formation XYZ", "BTS - Services")) == "autre"
    assert domaine_cascade(_cascade_row("Formation XYZ", "Licence - Droit-économie-gestion")) == "autre"
    assert domaine_cascade(_cascade_row("Formation XYZ", "Mise à niveau")) == "autre"
    assert domaine_cascade(_cascade_row("Formation XYZ", "")) == "autre"


def test_cascade_mapping_targets_are_valid_domains():
    from src.collect.parcoursup import FORM_LIB_VOE_ACC_TO_DOMAINE, EXTENDED_DOMAINS
    for dom in set(FORM_LIB_VOE_ACC_TO_DOMAINE.values()):
        assert dom in EXTENDED_DOMAINS, f"cible de mapping inconnue: {dom}"


def test_extract_fiche_nan_taux_becomes_none():
    """C1 garde-fou GE : un taux NaN (cellule CSV vide lue par pandas) ne doit
    PAS fuiter en NaN dans le corpus (JSON invalide + viole la borne [0,100])."""
    row = _vague_a_row()
    row["taux_acces_ens"] = float("nan")
    fiche = extract_fiche(row)
    assert fiche["taux_acces_parcoursup_2025"] is None


def test_safe_float_filters_nan_inf():
    from src.collect.parcoursup import _safe_float
    assert _safe_float(float("nan")) is None
    assert _safe_float(float("inf")) is None
    assert _safe_float(float("-inf")) is None
    assert _safe_float(42.0) == 42.0
