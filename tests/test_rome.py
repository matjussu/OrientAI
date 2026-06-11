from src.collect.rome import load_rome_job_titles, get_debouches_for_domain


def test_load_rome_returns_code_to_title_mapping(tmp_path):
    csv = tmp_path / "rome.csv"
    csv.write_text(
        '"code_rome","code_fiche_metier","code_ogr","libelle_rome","transition_eco","transition_num","transition_demo","emploi_reglemente","emploi_cadre","code_rome_parent"\n'
        '"M1844","11","6","Analyste en cybersécurité","","","","","","M1844"\n'
        '"M1811","12","7","Data engineer","","","","","","M1811"\n',
        encoding="utf-8",
    )
    mapping = load_rome_job_titles(csv)
    assert mapping["M1844"] == "Analyste en cybersécurité"
    assert mapping["M1811"] == "Data engineer"


def test_get_debouches_for_social_returns_K_codes_not_medical():
    """Order 2026-06-11 Fix 1 : le domaine 'social' (travail social) doit porter
    des débouchés ROME K* (action sociale), JAMAIS les J11xx médicaux.

    Régression : CESF / AES (NSF 332 Travail social) recevaient à tort les 10
    débouchés médicaux via domaine=sante. Le domaine 'social' canonise les
    métiers réels du travail social.
    """
    debouches = get_debouches_for_domain("social")
    assert len(debouches) >= 5
    codes = [d["code_rome"] for d in debouches]
    assert all(c.startswith("K") for c in codes), f"social doit être K*, got {codes}"
    assert not any(c.startswith("J") for c in codes), "AUCUN code médical J* dans social"
    assert all("code_rome" in d and "libelle" in d for d in debouches)
    # Cœur travail social : AES (K1306) + Assistant social (K1201)
    assert "K1306" in codes  # Accompagnant Educatif et Social
    assert "K1201" in codes  # Assistant de service social


def test_get_debouches_for_cyber_returns_rome_codes():
    debouches = get_debouches_for_domain("cyber")
    assert len(debouches) >= 5
    codes = [d["code_rome"] for d in debouches]
    assert "M1844" in codes  # Analyste en cybersécurité
    assert "M1812" in codes  # RSSI
    for d in debouches:
        assert d["libelle"]


def test_get_debouches_for_data_ia_returns_rome_codes():
    debouches = get_debouches_for_domain("data_ia")
    assert len(debouches) >= 3
    codes = [d["code_rome"] for d in debouches]
    assert "M1405" in codes  # Data scientist
    assert "M1811" in codes  # Data engineer


def test_get_debouches_for_unknown_domain_raises():
    import pytest
    with pytest.raises(KeyError):
        get_debouches_for_domain("unknown_domain")


# --- D3 extension tests (2026-04-19) : référentiel enrichi depuis zip ---

import pytest

from src.collect.rome import (
    get_rome_info,
    is_emploi_cadre,
    is_transition_numerique,
    list_all_rome_codes,
)


def test_rome_ref_loads_from_zip():
    """Le zip data/raw/rome_4_0.zip charge et contient >500 codes."""
    codes = list_all_rome_codes()
    if not codes:
        pytest.skip("data/raw/rome_4_0.zip absent — skip test d'intégration")
    assert len(codes) > 500
    # Codes historiques connus dans OrientIA
    assert "M1812" in codes  # RSSI
    assert "J1102" in codes  # Médecin généraliste


def test_get_rome_info_cyber():
    """M1812 (RSSI) doit revenir avec libellé non-vide."""
    codes = list_all_rome_codes()
    if not codes:
        pytest.skip("data/raw/rome_4_0.zip absent")
    info = get_rome_info("M1812")
    assert info is not None
    assert info.get("libelle")
    assert "code_rome" in info


def test_get_rome_info_returns_none_on_unknown():
    """Code inexistant ou vide → None (pas d'erreur)."""
    codes = list_all_rome_codes()
    if not codes:
        pytest.skip("data/raw/rome_4_0.zip absent")
    assert get_rome_info("ZZZZZ") is None
    assert get_rome_info("") is None


def test_rome_helpers_are_safe():
    """is_emploi_cadre et is_transition_numerique ne crashent jamais."""
    codes = list_all_rome_codes()
    if not codes:
        pytest.skip("data/raw/rome_4_0.zip absent")
    # Codes valides → bool
    assert isinstance(is_emploi_cadre("M1812"), bool)
    assert isinstance(is_transition_numerique("M1812"), bool)
    # Codes invalides → False (pas d'erreur)
    assert is_emploi_cadre("ZZZZZ") is False
    assert is_transition_numerique("") is False
