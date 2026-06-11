from src.collect.merge import merge_by_rncp, fuzzy_match_fiches, merge_all


def test_merge_by_rncp_joins_matching_codes():
    parcoursup = [
        {"nom": "Master IA", "ville": "Paris", "rncp": "12345", "taux_acces_parcoursup_2025": 25.0},
    ]
    onisep = [
        {"nom": "Master Intelligence Artificielle", "ville": "Paris", "rncp": "12345",
         "url_onisep": "http://onisep.fr/x"},
    ]
    merged = merge_by_rncp(parcoursup, onisep)
    assert len(merged) == 1
    assert merged[0]["rncp"] == "12345"
    assert merged[0]["taux_acces_parcoursup_2025"] == 25.0
    assert merged[0]["url_onisep"] == "http://onisep.fr/x"


def test_fuzzy_match_joins_similar_names():
    parcoursup_orphans = [
        {"nom": "Master Cybersécurité", "etablissement": "ENSIBS",
         "ville": "Vannes", "rncp": None, "taux_acces_parcoursup_2025": 18.0},
    ]
    onisep_orphans = [
        {"nom": "Master cyber", "etablissement": "ensibs",
         "ville": "vannes", "rncp": None, "url_onisep": "http://x"},
    ]
    merged = fuzzy_match_fiches(parcoursup_orphans, onisep_orphans, threshold=75)
    assert len(merged) == 1
    assert merged[0]["url_onisep"] == "http://x"


def test_merge_all_attaches_secnumedu_labels():
    parcoursup = [{"nom": "Master Cyber", "etablissement": "ENSIBS", "ville": "Vannes",
                   "rncp": None, "taux_acces_parcoursup_2025": 22.0}]
    onisep = []
    secnumedu = [{"nom": "Master Cyber", "etablissement": "ENSIBS", "ville": "Vannes",
                  "labels": ["SecNumEdu"]}]
    merged = merge_all(parcoursup, onisep, secnumedu)
    assert len(merged) == 1
    assert "SecNumEdu" in merged[0]["labels"]


def test_attach_labels_establishment_only_fallback():
    # Different formation names but same establishment — the new fallback should catch it
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "BUT Informatique parcours cyber",
         "etablissement": "EFREI Bordeaux",
         "ville": "Bordeaux",
         "domaine": "cyber",
         "labels": []},
    ]
    secnumedu = [
        {"nom": "Bachelor Cybersécurité EFREI",
         "etablissement": "EFREI",
         "ville": "",
         "labels": ["SecNumEdu"]},
    ]
    result = attach_labels(fiches, secnumedu)
    assert "SecNumEdu" in result[0]["labels"], \
        f"expected SecNumEdu label via establishment fallback, got {result[0]['labels']}"


def test_attach_labels_fallback_only_fires_for_cyber_domain():
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "Master IA",
         "etablissement": "EFREI",
         "ville": "Paris",
         "domaine": "data_ia",  # NOT cyber
         "labels": []},
    ]
    secnumedu = [
        {"nom": "Bachelor EFREI",
         "etablissement": "EFREI",
         "ville": "",
         "labels": ["SecNumEdu"]},
    ]
    result = attach_labels(fiches, secnumedu)
    assert "SecNumEdu" not in (result[0]["labels"] or []), \
        "SecNumEdu label should not be attached to data_ia domain via the cyber-only fallback"


def test_attach_labels_manual_table_labels_known_school():
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "Ingénieur Cybersécurité", "etablissement": "ENSIBS",
         "ville": "Vannes", "domaine": "cyber", "labels": []},
    ]
    manual = [{"etab_normalized": "ensibs", "labels": ["SecNumEdu", "CTI"]}]
    result = attach_labels(fiches, [], manual_table=manual)
    assert "SecNumEdu" in result[0]["labels"]
    assert "CTI" in result[0]["labels"]


def test_attach_labels_manual_table_explicitly_blocks_unlabeled_school():
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "Master Cyber", "etablissement": "EPITA Paris",
         "ville": "Paris", "domaine": "cyber", "labels": []},
    ]
    manual = [{"etab_normalized": "epita", "labels": []}]
    # Empty secnumedu list so stages 1/2 can't fire
    result = attach_labels(fiches, [], manual_table=manual)
    assert result[0]["labels"] == []  # Correctly no label attached


def test_attach_labels_manual_table_overrides_earlier_stages():
    """Manual table must override labels from Stages 1/2.

    Before this fix, Stage 3 only appended to existing_labels, so a fuzzy
    match in Stage 1 could attach SecNumEdu to an EPITA fiche and Stage 3's
    blocklist entry wouldn't remove it.
    """
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "bachelor cybersecurite epita",
         "etablissement": "EPITA",
         "ville": "Paris", "domaine": "cyber", "labels": []},
    ]
    # Non-empty SecNumEdu list with a near-identical entry — will match Stage 1
    secnumedu = [
        {"nom": "bachelor cybersecurite epita",
         "etablissement": "EPITA",
         "ville": "Paris",
         "labels": ["SecNumEdu"]},
    ]
    manual = [{"etab_normalized": "epita", "labels": []}]
    result = attach_labels(fiches, secnumedu, manual_table=manual)
    assert result[0]["labels"] == [], \
        f"EPITA manual blocklist didn't override Stage 1 match: got {result[0]['labels']}"


def test_attach_labels_manual_table_replaces_not_appends():
    """Manual-table labels REPLACE prior labels (they don't merge)."""
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "bachelor cybersecurite efrei",
         "etablissement": "EFREI Bordeaux",
         "ville": "Bordeaux", "domaine": "cyber", "labels": ["SomeStaleLabel"]},
    ]
    manual = [{"etab_normalized": "efrei", "labels": ["SecNumEdu", "CTI"]}]
    result = attach_labels(fiches, [], manual_table=manual)
    # Final labels must be exactly what the manual table says (order-insensitive),
    # not the union of stale + manual labels
    assert set(result[0]["labels"]) == {"SecNumEdu", "CTI"}
    assert "SomeStaleLabel" not in result[0]["labels"]


def test_attach_labels_manual_table_ignores_non_tech_domains():
    """Vague santé fix : the manual_labels.json is all cyber-oriented
    (SecNumEdu, CTI, CGE, Grade Master). It must NOT leak to santé
    or other non-tech domains just because the establishment is shared
    (e.g., Université de Limoges hosts both cyber AND PASS santé —
    the cyber label entry must only apply to the cyber fiche)."""
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "Licence PASS",
         "etablissement": "Université de Limoges",
         "ville": "Limoges", "domaine": "sante", "labels": []},
        {"nom": "Master Cybersécurité",
         "etablissement": "Université de Limoges",
         "ville": "Limoges", "domaine": "cyber", "labels": []},
    ]
    # etab_normalized must match the output of normalize_name (stopwords removed)
    manual = [
        {"etab_normalized": "universite limoges", "labels": ["SecNumEdu", "CTI"]}
    ]
    result = attach_labels(fiches, [], manual_table=manual)
    # The santé fiche must NOT receive SecNumEdu
    assert result[0]["domaine"] == "sante"
    assert "SecNumEdu" not in (result[0]["labels"] or [])
    # The cyber fiche correctly receives the manual labels
    assert "SecNumEdu" in result[1]["labels"]


def test_attach_labels_manual_table_substring_match_both_ways():
    from src.collect.merge import attach_labels
    # Fiche etab is longer than manual entry ("telecom paris" in "telecom paris institut")
    fiches1 = [{"nom": "MS Cyber", "etablissement": "Télécom Paris Institut",
                "ville": "Palaiseau", "domaine": "cyber", "labels": []}]
    manual = [{"etab_normalized": "telecom paris", "labels": ["SecNumEdu"]}]
    result = attach_labels(fiches1, [], manual_table=manual)
    assert "SecNumEdu" in result[0]["labels"]

    # Fiche etab is shorter than manual entry ("efrei" in "efrei paris")
    fiches2 = [{"nom": "Bachelor", "etablissement": "EFREI",
                "ville": "Villejuif", "domaine": "cyber", "labels": []}]
    manual2 = [{"etab_normalized": "efrei paris pantheon", "labels": ["SecNumEdu"]}]
    result2 = attach_labels(fiches2, [], manual_table=manual2)
    assert "SecNumEdu" in result2[0]["labels"]


# === Vague A — attach_debouches + attach_metadata integration in pipeline ===


def test_attach_debouches_injects_rome_codes_per_domain():
    from src.collect.merge import attach_debouches
    fiches = [
        {"nom": "Master Cyber", "domaine": "cyber"},
        {"nom": "Master IA", "domaine": "data_ia"},
    ]
    enriched = attach_debouches(fiches)
    cyber = enriched[0]["debouches"]
    data = enriched[1]["debouches"]
    assert len(cyber) == 9, f"cyber domain should have 9 ROME codes, got {len(cyber)}"
    assert len(data) == 6, f"data_ia domain should have 6 ROME codes, got {len(data)}"
    assert all("code_rome" in d and "libelle" in d for d in cyber)
    # Sanity: known cyber RSSI code must be present
    assert any(d["code_rome"] == "M1812" for d in cyber)


def test_attach_debouches_does_not_clobber_existing():
    from src.collect.merge import attach_debouches
    preset = [{"code_rome": "X9999", "libelle": "custom"}]
    fiches = [{"nom": "x", "domaine": "cyber", "debouches": preset}]
    enriched = attach_debouches(fiches)
    assert enriched[0]["debouches"] == preset, \
        "attach_debouches must not overwrite pre-existing debouches"


def test_attach_debouches_empty_for_missing_domain():
    from src.collect.merge import attach_debouches
    fiches = [{"nom": "Unclassified"}]
    enriched = attach_debouches(fiches)
    assert enriched[0]["debouches"] == []


# === Order 2026-06-11 — fix mapping ROME J11 : travail social ≠ santé ===
# Root cause : NSF 332 "Travail social" + parcoursup "secteur social" mappaient
# sur domaine=sante -> attach_debouches injectait les 10 ROME médicaux J11xx à
# ~392 formations sociales (CESF, AES, éducateur spé). detresse-007 = la pointe.


def test_nsf_332_travail_social_maps_to_social_not_sante():
    """NSF 332 = 'Travail social', distinct de 331 (Santé) / 344 (Techno méd.).
    Régression : mappait 'sante' -> débouchés médicaux J11xx aux formations sociales."""
    from src.collect.merge import _infer_domaine_from_nsf
    assert _infer_domaine_from_nsf([{"code": "332"}]) == "social"
    # Les vrais codes santé restent santé
    assert _infer_domaine_from_nsf([{"code": "331"}]) == "sante"
    assert _infer_domaine_from_nsf([{"code": "344"}]) == "sante"


def test_is_social_work_formation_predicate():
    """Prédicat déterministe travail social. Précis : capte le social, JAMAIS
    le paramédical/médical (qui doit garder ses débouchés santé légitimes)."""
    from src.collect.merge import is_social_work_formation
    # Travail social (NSF 332) — True
    assert is_social_work_formation("ACCOMPAGNANT EDUCATIF ET SOCIAL (DIPLOME D'ETAT)")
    assert is_social_work_formation("Conseiller en économie sociale familiale")
    assert is_social_work_formation("Diplôme d'État d'éducateur spécialisé")
    assert is_social_work_formation("Assistant de service social")
    assert is_social_work_formation("Technicien d'intervention sociale et familiale")
    assert is_social_work_formation("Moniteur éducateur")
    assert is_social_work_formation("DE Éducateur de jeunes enfants")
    # Santé / paramédical / autre — False (garde ses débouchés)
    assert not is_social_work_formation("Diplôme d'État d'infirmier")
    assert not is_social_work_formation("Aide-soignant")
    assert not is_social_work_formation("Masseur-kinésithérapeute")
    assert not is_social_work_formation("PASS - accès santé")
    assert not is_social_work_formation("Master Cybersécurité")
    assert not is_social_work_formation("Licence de sciences sociales")  # discipline, pas métier social
    # Garde-fou paramédical : une profession santé en structure médico-sociale
    # reste santé (le terme "médico-social" ne doit pas l'emporter sur "infirmier").
    assert not is_social_work_formation(
        "Exercer une mission de coordinateur infirmier dans une structure médico-sociale"
    )
    # Carrières Sociales (BUT travail social) — True (faux négatif récupéré)
    assert is_social_work_formation("Carrières sociales : Éducation spécialisée")
    assert is_social_work_formation("Carrières Sociales : Animation Sociale et Socioculturelle")


def test_reclassify_social_health_moves_social_out_of_sante():
    """La passe de reclassification déterministe sort les formations travail
    social du domaine 'sante' (chokepoint avant attach_debouches)."""
    from src.collect.merge import reclassify_social_health
    fiches = [
        {"nom": "ACCOMPAGNANT EDUCATIF ET SOCIAL", "domaine": "sante"},
        {"nom": "Conseiller en économie sociale familiale", "domaine": "sante"},
        {"nom": "Diplôme d'État d'infirmier", "domaine": "sante"},   # vraie santé : inchangé
        {"nom": "Master Cyber", "domaine": "cyber"},                 # intouché
    ]
    out = reclassify_social_health(fiches)
    assert out[0]["domaine"] == "social"
    assert out[1]["domaine"] == "social"
    assert out[2]["domaine"] == "sante", "une formation santé réelle reste santé"
    assert out[3]["domaine"] == "cyber"


def test_social_formation_gets_no_medical_debouches_end_to_end():
    """Intégration reclassify -> attach_debouches : une formation travail social
    ne sort JAMAIS avec un débouché médical J11xx."""
    from src.collect.merge import reclassify_social_health, attach_debouches
    fiches = reclassify_social_health(
        [{"nom": "Conseiller en économie sociale familiale", "domaine": "sante"}]
    )
    fiches = attach_debouches(fiches)
    codes = [d["code_rome"] for d in fiches[0]["debouches"]]
    assert codes, "social doit avoir des débouchés (K*)"
    assert not any(c.startswith("J") for c in codes), \
        f"AUCUN débouché médical J* sur une formation sociale, got {codes}"
    assert all(c.startswith("K") for c in codes)


def test_attach_metadata_populates_provenance_and_dates():
    from src.collect.merge import attach_metadata
    fiches = [{
        "nom": "M", "domaine": "cyber",
        "cod_aff_form": "42",
        "taux_acces_parcoursup_2025": 18.0,
        "url_onisep": "http://x", "type_diplome": "master",
        "labels": ["SecNumEdu"],
        "admission": {"session": 2025},
        "profil_admis": {"mentions_pct": {"tb": 45.0}},
        "debouches": [{"code_rome": "M1812", "libelle": "RSSI"}],
        "match_method": "rncp",
    }]
    enriched = attach_metadata(fiches, collection_date="2026-04-17")
    f = enriched[0]
    # provenance: maps each enriched field to its origin
    assert f["provenance"]["admission"] == "parcoursup_2025"
    assert f["provenance"]["profil_admis"] == "parcoursup_2025"
    assert f["provenance"]["debouches"] == "rome_4_0"
    assert f["provenance"]["type_diplome"] == "onisep"
    assert f["provenance"]["labels"] == "secnumedu+manual"
    # collected_at: date per source
    assert f["collected_at"]["parcoursup"] == "2026-04-17"
    assert f["collected_at"]["onisep"] == "2026-04-17"
    assert f["collected_at"]["rome"] == "2026-04-17"
    # merge_confidence: 1.0 for RNCP match
    assert f["merge_confidence"]["parcoursup"] == 1.0
    assert f["merge_confidence"]["onisep"] == 1.0


def test_attach_metadata_fuzzy_confidence_reflects_score():
    from src.collect.merge import attach_metadata
    fiches = [{
        "nom": "M", "domaine": "cyber",
        "url_onisep": "http://x",
        "taux_acces_parcoursup_2025": 30.0,
        "match_method": "fuzzy_87.5",
    }]
    enriched = attach_metadata(fiches, collection_date="2026-04-17")
    assert enriched[0]["merge_confidence"]["onisep"] == 0.88  # round(0.875, 2)


def test_attach_metadata_parcoursup_only_marks_onisep_null():
    from src.collect.merge import attach_metadata
    fiches = [{
        "nom": "M", "domaine": "cyber",
        "taux_acces_parcoursup_2025": 30.0,
        "match_method": "parcoursup_only",
    }]
    enriched = attach_metadata(fiches, collection_date="2026-04-17")
    # parcoursup_only = ONISEP was not joined; confidence.onisep must be null (=None)
    assert enriched[0]["merge_confidence"]["parcoursup"] == 1.0
    assert enriched[0]["merge_confidence"].get("onisep") is None


# === Tests merge_all_extended — ADR-039 scope élargi ===


def test_monmaster_to_fiche_preserves_phase_and_schema():
    from src.collect.merge import monmaster_to_fiche

    mm = {
        "source": "monmaster",
        "phase": "master",
        "nom": "Master Informatique — Data Science",
        "etablissement": "Université X",
        "ville": "Paris",
        "niveau": "bac+5",
        "discipline": "Sciences économiques, gestion",
        "mention": "INFORMATIQUE",
    }
    fiche = monmaster_to_fiche(mm)
    assert fiche["phase"] == "master"
    assert fiche["niveau"] == "bac+5"
    assert fiche["match_method"] == "monmaster_only"
    assert fiche["domaine"] == "eco_gestion"
    assert fiche["statut"] == "Public"
    assert fiche["labels"] == []


def test_monmaster_to_fiche_infers_data_ia_from_informatique_discipline():
    from src.collect.merge import monmaster_to_fiche
    mm = {
        "phase": "master",
        "nom": "Master X",
        "discipline": "Informatique scientifique",
    }
    assert monmaster_to_fiche(mm)["domaine"] == "data_ia"


def test_monmaster_to_fiche_fallback_domaine_autre():
    from src.collect.merge import monmaster_to_fiche
    assert monmaster_to_fiche({"discipline": "Exotique rare"})["domaine"] == "autre"


def test_rncp_to_fiche_maps_intitule_to_nom():
    from src.collect.merge import rncp_to_fiche
    certif = {
        "source": "rncp",
        "phase": "initial",
        "intitule": "Analyste cybersécurité",
        "numero_fiche": "RNCP35521",
        "niveau": "bac+3",
        "niveau_eu": "NIV6",
        "abrege_type": "TP",
        "abrege_intitule": "Titre professionnel",
        "actif": True,
        "voies_acces": ["Apprentissage", "VAE"],
        "codes_rome": [{"code": "M1844", "libelle": "Analyste cybersécurité"}],
        "codes_nsf": [{"code": "326", "libelle": "Informatique"}],
        "certificateurs": [{"siret": "123", "nom": "Ministère du Travail"}],
    }
    fiche = rncp_to_fiche(certif)
    assert fiche["nom"] == "Analyste cybersécurité"
    assert fiche["rncp"] == "RNCP35521"
    assert fiche["etablissement"] == "Ministère du Travail"
    assert fiche["ville"] == ""
    assert fiche["niveau"] == "bac+3"
    assert fiche["domaine"] == "data_ia"  # NSF 326 = informatique
    assert fiche["statut"] == "Certificat RNCP"
    assert "Apprentissage" in fiche["voies_acces"]


def test_rncp_to_fiche_handles_no_certificateurs():
    from src.collect.merge import rncp_to_fiche
    certif = {"intitule": "X", "numero_fiche": "RNCP1", "certificateurs": []}
    fiche = rncp_to_fiche(certif)
    assert fiche["etablissement"] == ""
    assert fiche["domaine"] == "autre"


def test_rncp_to_fiche_infers_domaine_sante_from_rome_j():
    from src.collect.merge import rncp_to_fiche
    certif = {
        "intitule": "Aide-soignant",
        "numero_fiche": "RNCP100",
        "codes_rome": [{"code": "J1501", "libelle": "IDE"}],
    }
    assert rncp_to_fiche(certif)["domaine"] == "sante"


def test_attach_cereq_insertion_enriches_matching_fiches():
    from src.collect.merge import attach_cereq_insertion
    fiches = [
        {"niveau": "bac+5", "domaine": "Informatique"},
        {"niveau": "bac+3", "domaine": "Droit"},
    ]
    cereq = [
        {
            "niveau": "bac+5", "domaine": "Informatique", "cohorte": "Generation 2017",
            "taux_emploi_3ans": 0.92, "salaire_median_embauche": 2450,
        },
    ]
    enriched = attach_cereq_insertion(fiches, cereq)
    assert enriched[0]["insertion_pro"]["taux_emploi_3ans"] == 0.92
    assert enriched[0]["insertion_pro"]["salaire_median_embauche"] == 2450
    # Pas de match pour la 2ème fiche
    assert "insertion_pro" not in enriched[1]


def test_attach_cereq_insertion_no_op_if_empty():
    from src.collect.merge import attach_cereq_insertion
    fiches = [{"niveau": "bac+5", "domaine": "Informatique"}]
    assert attach_cereq_insertion(fiches, None) == fiches
    assert attach_cereq_insertion(fiches, []) == fiches


def test_merge_all_extended_backward_compat_without_new_sources():
    """Sans monmaster/rncp/cereq, le résultat doit être identique à merge_all()."""
    from src.collect.merge import merge_all_extended, merge_all
    parcoursup = [{"nom": "M IA", "rncp": "1", "domaine": "cyber"}]
    onisep = [{"nom": "M IA", "rncp": "1", "domaine": "cyber"}]
    legacy = merge_all(parcoursup, onisep, secnumedu=[])
    extended = merge_all_extended(parcoursup, onisep, secnumedu=[])
    # Tous les champs legacy doivent être présents à l'identique
    assert len(extended) == len(legacy)
    for le, ex in zip(legacy, extended):
        assert le.get("rncp") == ex.get("rncp")
        assert le.get("nom") == ex.get("nom")


def test_merge_all_extended_adds_monmaster_fiches():
    from src.collect.merge import merge_all_extended
    mm = [{
        "source": "monmaster", "phase": "master", "nom": "Master X",
        "etablissement": "Univ Y", "ville": "Lyon", "niveau": "bac+5",
        "discipline": "Droit",
    }]
    out = merge_all_extended([], [], secnumedu=[], monmaster=mm)
    mm_fiches = [f for f in out if f.get("source") == "monmaster"]
    assert len(mm_fiches) == 1
    assert mm_fiches[0]["phase"] == "master"
    assert mm_fiches[0]["domaine"] == "droit"


def test_merge_all_extended_adds_rncp_certifs():
    from src.collect.merge import merge_all_extended
    rncp = [{
        "intitule": "Assistant comptable", "numero_fiche": "RNCP200",
        "niveau": "bac+2", "niveau_eu": "NIV5", "phase": "initial",
        "codes_rome": [{"code": "M1203"}],
        "codes_nsf": [{"code": "314t"}],  # Comptabilité
        "certificateurs": [],
    }]
    out = merge_all_extended([], [], secnumedu=[], rncp=rncp)
    rncp_fiches = [f for f in out if f.get("source") == "rncp"]
    assert len(rncp_fiches) == 1
    assert rncp_fiches[0]["nom"] == "Assistant comptable"
    assert rncp_fiches[0]["phase"] == "initial"


def test_merge_all_extended_cereq_enrichment_applied_across_sources():
    from src.collect.merge import merge_all_extended
    mm = [{
        "source": "monmaster", "phase": "master", "niveau": "bac+5",
        "discipline": "Sciences économiques, gestion", "nom": "M",
    }]
    cereq = [{
        "niveau": "bac+5", "domaine": "eco_gestion", "cohorte": "Generation 2017",
        "taux_emploi_3ans": 0.88,
    }]
    out = merge_all_extended([], [], secnumedu=[], monmaster=mm, cereq=cereq)
    # La fiche MonMaster doit être enrichie Céreq par niveau+domaine
    mm_fiche = next(f for f in out if f.get("source") == "monmaster")
    assert mm_fiche.get("insertion_pro", {}).get("taux_emploi_3ans") == 0.88


def test_merge_all_extended_phase_default_for_legacy_parcoursup():
    """Parcoursup legacy (sans phase explicite) → phase inférée."""
    from src.collect.merge import merge_all_extended
    parcoursup = [
        {"nom": "BTS X", "niveau": "bac+2", "domaine": "cyber"},
        {"nom": "M5 IA", "niveau": "bac+5", "domaine": "cyber"},
    ]
    out = merge_all_extended(parcoursup, [], secnumedu=[])
    by_nom = {f["nom"]: f for f in out}
    assert by_nom["BTS X"]["phase"] == "initial"
    assert by_nom["M5 IA"]["phase"] == "master"
