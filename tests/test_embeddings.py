from unittest.mock import MagicMock, patch
from src.rag.embeddings import embed_texts, fiche_to_text, _salary_fragment


def test_dense_sigle_injection_parked_by_default():
    """J2 sigle dense PARKÉ (ordre 0825) : par défaut (ORIENTIA_DENSE_SIGLE non set),
    le sigle n'est PAS injecté dans le texte embeddé — protège la baseline d'une
    régression connue (déplace MIAGE Paris hors top-10). La logique sigle reste
    intacte (réactivable post-VivaTech)."""
    from src.rag.sigle_expand import sigle_injection_text
    from src.rag import embeddings as emb
    fiche = {"nom": "BUT Génie électrique et informatique industrielle",
             "etablissement": "IUT d'Allier", "ville": "Montluçon"}
    # logique sigle intacte : un sigle EST détecté sur cette fiche
    assert sigle_injection_text(fiche), "fixture invalide : aucun sigle détecté"
    # mais le flag dense est OFF par défaut -> pas d'injection dans l'embed
    assert emb._DENSE_SIGLE_INJECTION is False, "ORIENTIA_DENSE_SIGLE ne doit pas être set en CI/dev"
    assert "Sigle :" not in fiche_to_text(fiche)


def test_salary_fragment_includes_quartile_range_when_present():
    """Phase 1 (order 0825) : la fourchette Q1-Q3 doit apparaître dans le fragment
    salaire pour devenir retrievable via l'embedding."""
    sf = _salary_fragment({
        "salaire_median_embauche": 1850, "salaire_q1": 1600, "salaire_q3": 2200,
        "salaire_net": True, "salaire_horizon": "12m",
    })
    assert "1850" in sf and "net" in sf
    assert "1600" in sf and "2200" in sf  # fourchette présente


def test_salary_fragment_no_range_when_quartiles_absent():
    """Médiane seule -> pas de fourchette (ni '1600-' inventé)."""
    sf = _salary_fragment({"salaire_median_embauche": 1850, "salaire_net": True})
    assert "1850" in sf
    assert "fourchette" not in sf.lower()


def test_fiche_to_text_salary_direct_schema_surfaces_quartiles():
    """Schéma salaire-direct InserSup (insertion_pro sans bloc taux) : le texte
    embeddé doit porter la fourchette pour la retrievabilité."""
    fiche = {
        "nom": "Master Acoustique", "etablissement": "Université X",
        "insertion_pro": {
            "salaire_median_embauche": 1850, "salaire_q1": 1600, "salaire_q3": 2200,
            "salaire_net": True, "salaire_horizon": "12m", "salaire_source": "insersup",
        },
    }
    out = fiche_to_text(fiche)
    assert "1600" in out and "2200" in out


def test_fiche_to_text_includes_key_fields():
    fiche = {
        "nom": "Master Cyber",
        "etablissement": "ENSIBS",
        "ville": "Vannes",
        "statut": "Public",
        "labels": ["SecNumEdu"],
        "taux_acces_parcoursup_2025": 22.0,
    }
    text = fiche_to_text(fiche)
    assert "Master Cyber" in text
    assert "ENSIBS" in text
    assert "Vannes" in text
    assert "SecNumEdu" in text
    assert "22" in text


def test_embed_texts_calls_mistral_api():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    mock_client.embeddings.create.return_value = mock_response

    result = embed_texts(mock_client, ["hello"])
    assert result == [[0.1, 0.2, 0.3]]
    mock_client.embeddings.create.assert_called_once_with(
        model="mistral-embed", inputs=["hello"]
    )


# === Vague B.3 — fiche_to_text enriched ===


def test_fiche_to_text_vague_b3_detail_extended_to_800_chars():
    """Vague B.3: detail window expanded from 200 → 800 chars so
    the embedding carries specialisation/parcours signal for better
    retrieval on 'formations cyber' / 'data science' type queries."""
    fiche = {
        "nom": "Master Cyber",
        "etablissement": "ENSIBS",
        "ville": "Vannes",
        "statut": "Public",
        "labels": ["SecNumEdu"],
        "detail": "A" * 900,  # 900 chars
    }
    text = fiche_to_text(fiche)
    # detail should be included up to 800 chars (not the old 200)
    assert "Détail" in text
    detail_part = text.split("Détail : ", 1)[1]
    # The Détail segment must be at least 500 chars long (some joiner
    # content after it is fine).
    assert len(detail_part) >= 500, (
        f"detail window too narrow: got {len(detail_part)} chars after 'Détail : '"
    )


def test_fiche_to_text_vague_b3_includes_rome_libelles():
    """Vague B.3: ROME job libellés injected (codes excluded). This carries
    semantic signal like 'RSSI', 'Data scientist', 'Architecte sécurité'
    that matches career-oriented queries ('je veux être data scientist')."""
    fiche = {
        "nom": "Master Cyber",
        "etablissement": "ENSIBS",
        "ville": "Vannes",
        "statut": "Public",
        "labels": ["SecNumEdu"],
        "debouches": [
            {"code_rome": "M1812", "libelle": "Responsable de la Sécurité des Systèmes d'Information (RSSI)"},
            {"code_rome": "M1405", "libelle": "Data scientist"},
        ],
    }
    text = fiche_to_text(fiche)
    assert "Métiers possibles" in text
    assert "RSSI" in text
    assert "Data scientist" in text


def test_fiche_to_text_vague_b3_excludes_rome_codes_from_embedding():
    """Codes (M1812 etc.) stay out of the embedding — they are structured
    identifiers, not narrative content. Libellés are narrative and help
    retrieval; codes pollute it with shared-across-domain signal."""
    fiche = {
        "nom": "Master Cyber", "etablissement": "E", "ville": "V",
        "debouches": [{"code_rome": "M1812", "libelle": "RSSI"}],
    }
    text = fiche_to_text(fiche)
    assert "M1812" not in text, "ROME codes must stay out of the embedding"


def test_fiche_to_text_vague_b3_no_metiers_line_when_debouches_empty():
    fiche = {
        "nom": "F", "etablissement": "E", "ville": "V",
        "debouches": [],
    }
    text = fiche_to_text(fiche)
    assert "Métiers possibles" not in text


def test_fiche_to_text_sprint12_d1_includes_profil_admis():
    """Sprint 12 D1 (2026-05-01) — REVERSAL explicite du choix
    Vague B.3 d'exclure profil_admis. Cf
    docs/sprint12-D1-profil-admis-audit-champs-2026-05-01.md.

    Rationale du reversal : v3 admission_stats (Run F, 2026-04-24) avait
    déjà commencé à injecter des chiffres dans l'embedding (taux d'accès
    Parcoursup, salaire médian Céreq). Le principe "numbers pollute
    similarity" du test précédent était théorique ; en pratique, Sprint
    11 P1.1 a montré que NE PAS exposer les chiffres profil-spécifiques
    cause des hallucinations LLM (Q1 Paris-Saclay 27 % inventé, EPF 95 %
    inventé) = problème pire que la pollution similarité hypothétique.
    """
    fiche = {
        "nom": "F", "etablissement": "E", "ville": "V",
        "profil_admis": {
            "mentions_pct": {"tb": 45.0, "b": 30.0},
            "bac_type_pct": {"general": 80.0, "techno": 15.0},
            "boursiers_pct": 20.0, "femmes_pct": 24.0,
        },
    }
    text = fiche_to_text(fiche)
    # Profil des admis section présente
    assert "Profil des admis" in text
    # Mentions au bac présentes (skip ab=0 et sans=0)
    assert "45 % très bien" in text
    assert "30 % bien" in text
    # Type bac présent (skip pro=0)
    assert "80 % bac général" in text
    assert "15 % bac techno" in text
    # Démographie présente (skip ce qui = 0)
    assert "20 % boursiers" in text
    assert "24 % femmes" in text


# ---------- Sprint 12 D1 — _format_profil_admis helper unit tests ----------

from src.rag.embeddings import _format_profil_admis


def test_format_profil_admis_riche_complet():
    """Cas EFREI Bordeaux Bachelor cyber (sample audit S1) — 7 sous-champs
    tous remplis et meaningful → 4 sections dans la chaîne."""
    pa = {
        "mentions_pct": {"tb": 4.0, "b": 12.0, "ab": 29.0, "sans": 54.0},
        "bac_type_pct": {"general": 71.0, "techno": 17.0, "pro": 12.0},
        "acces_pct":    {"general": 79.0, "techno": 14.0, "pro": 6.0},
        "boursiers_pct": 21.0,
        "femmes_pct": 10.0,
        "neobacheliers_pct": 77.0,
        "origine_academique_idf_pct": 58.0,
    }
    out = _format_profil_admis(pa)
    assert out is not None
    assert out.startswith("Profil des admis (Parcoursup 2025) :")
    # 4 sections séparées par " — "
    assert "mentions au bac : 4 % très bien, 12 % bien, 29 % assez bien, 54 % sans mention" in out
    assert "type de bac admis : 71 % bac général, 17 % bac techno, 12 % bac pro" in out
    assert "taux d'accès par profil : 79 % pour bac général, 14 % pour bac techno, 6 % pour bac pro" in out
    assert "profil démographique : 21 % boursiers, 10 % femmes, 77 % néobacheliers, 58 % origine académique Île-de-France" in out


def test_format_profil_admis_partiel_mentions_seule():
    """Sous-champ mentions_pct rempli, le reste vide ou tous-zéros → on
    garde mentions seule, on skip le reste."""
    pa = {
        "mentions_pct": {"tb": 10.0, "b": 25.0, "ab": 40.0, "sans": 25.0},
        "bac_type_pct": {"general": 0, "techno": 0, "pro": 0},
        "acces_pct": {},
        "boursiers_pct": 0,
        "femmes_pct": 0.0,
    }
    out = _format_profil_admis(pa)
    assert out is not None
    assert "mentions au bac" in out
    # Pas de section vide (skip)
    assert "type de bac admis" not in out
    assert "taux d'accès par profil" not in out
    assert "profil démographique" not in out


def test_format_profil_admis_partiel_bac_type_seul():
    pa = {
        "bac_type_pct": {"general": 65.0, "techno": 30.0, "pro": 5.0},
        # autres champs absents
    }
    out = _format_profil_admis(pa)
    assert out is not None
    assert "type de bac admis" in out
    assert "65 % bac général" in out
    assert "mentions au bac" not in out


def test_format_profil_admis_tous_zeros_returns_none():
    """Cas placeholder Parcoursup ~81 % du corpus — retourne None,
    aucune pollution embedding avec des "0 %" non-informatifs."""
    pa = {
        "mentions_pct": {"tb": 0.0, "b": 0.0, "ab": 0.0, "sans": 0.0},
        "bac_type_pct": {"general": 0.0, "techno": 0.0, "pro": 0.0},
        "acces_pct": {"general": 0.0, "techno": 0.0, "pro": 0.0},
        "boursiers_pct": 0.0,
        "femmes_pct": 0.0,
        "neobacheliers_pct": 0.0,
        "origine_academique_idf_pct": 0.0,
    }
    assert _format_profil_admis(pa) is None


def test_format_profil_admis_absent_returns_none():
    assert _format_profil_admis(None) is None
    assert _format_profil_admis({}) is None


def test_format_profil_admis_valeurs_limites():
    """100 % et 0.5 % doivent être correctement formatés (arrondi entier
    pour stabilité retrieval, cohérent avec _safe_pct)."""
    pa = {
        "mentions_pct": {"tb": 100.0, "b": 0.5},  # 0.5 → arrondi à 0 → skip
        "boursiers_pct": 0.7,  # arrondi à 1 % → garder
    }
    out = _format_profil_admis(pa)
    assert out is not None
    assert "100 % très bien" in out
    # 0.5 → round(0.5) = 0 (banker's rounding) ou 1 selon Python ; les deux acceptables
    # le test ne fixe pas le comportement exact pour ce edge case
    assert "1 % boursiers" in out


def test_format_profil_admis_type_invalid_returns_none():
    """Robustesse : profil_admis = string ou int ne crash pas, retourne None."""
    assert _format_profil_admis("not a dict") is None  # type: ignore[arg-type]
    assert _format_profil_admis(42) is None  # type: ignore[arg-type]


def test_format_profil_admis_sous_champ_invalid_skip_silently():
    """Si mentions_pct est une string au lieu de dict (donnée corrompue),
    on skip ce sous-champ proprement sans crash."""
    pa = {
        "mentions_pct": "corrupted",
        "bac_type_pct": {"general": 50.0, "techno": 50.0, "pro": 0},
    }
    out = _format_profil_admis(pa)
    assert out is not None
    assert "type de bac admis" in out
    assert "mentions au bac" not in out


# -------- Chantier C+ 2026-05-13 — Exploitation champ `text` pour fiches annexes --------


class TestFicheToTextAnnexesChantierCPlus:
    """Chantier C+ (2026-05-13) : fiches `domain != none` avec champ `text`
    substantiel doivent utiliser un préfixe [domain] + Region + métier/sujet,
    puis le contenu du champ `text` directement. Aucun changement pour les
    fiches Parcoursup (`domain` absent), qui conservent le format v4 éprouvé.
    """

    def test_dares_metier_prospective_uses_text_field(self):
        """Fiche DARES Métiers 2030 : embed inclut fap_libelle + text."""
        from src.rag.embeddings import fiche_to_text
        fiche = {
            "domain": "metier_prospective",
            "fap_libelle": "Maraîchers, jardiniers, viticulteurs",
            "region": "Occitanie",
            "text": (
                "Métier 2030 (DARES) — Maraîchers, jardiniers, viticulteurs en "
                "Occitanie (FAP A1Z) | Effectifs 2019 : 40.9k | Postes à pourvoir "
                "à l'horizon 2030 : 9.8k | Tension marché 2019 : niveau 2."
            ),
        }
        out = fiche_to_text(fiche)
        assert out.startswith("[metier_prospective]")
        assert "Région : Occitanie" in out
        assert "Métier : Maraîchers, jardiniers, viticulteurs" in out
        assert "DARES" in out
        assert "Postes à pourvoir" in out
        assert len(out) >= 200

    def test_crous_fiche_uses_text_field(self):
        from src.rag.embeddings import fiche_to_text
        fiche = {
            "domain": "crous",
            "subject": "Résidences universitaires Lyon",
            "text": (
                "CROUS Lyon — Résidences universitaires : Studios T1 entre 380€ et "
                "450€/mois CC. Chambres en cité U entre 180€ et 240€/mois CC. "
                "12 résidences gérées par CROUS Lyon."
            ),
        }
        out = fiche_to_text(fiche)
        assert out.startswith("[crous]")
        assert "Sujet : Résidences universitaires Lyon" in out
        assert "Studios T1" in out
        assert "CROUS Lyon" in out

    def test_insee_salaire_uses_text_field(self):
        from src.rag.embeddings import fiche_to_text
        fiche = {
            "domain": "insee_salaire",
            "text": (
                "Salaires PCS 37 : Cadres administratifs et commerciaux d'entreprises "
                "(France 2023) | Effectif : 1.2M | Salaire net médian annuel : 45 200 € "
                "| Médian mensuel : 3 767 €."
            ),
        }
        out = fiche_to_text(fiche)
        assert out.startswith("[insee_salaire]")
        assert "PCS 37" in out
        assert "45 200" in out or "45200" in out

    def test_rome_metier_detail_uses_text_field(self):
        from src.rag.embeddings import fiche_to_text
        fiche = {
            "domain": "metier_detail",
            "libelle_metier": "Actuaire",
            "text": (
                "Métier ROME C1107 : Actuaire | Compétences : modélisation, "
                "statistiques, analyse de risques, assurance, finance. "
                "Niveau d'études : bac+5 minimum."
            ),
        }
        out = fiche_to_text(fiche)
        assert out.startswith("[metier_detail]")
        assert "Métier : Actuaire" in out
        assert "modélisation" in out

    def test_parcoursup_fiche_unchanged_no_domain(self):
        """Critique : les fiches Parcoursup (domain absent) restent au format v4
        exact. Aucune régression possible sur le cœur de production éprouvé."""
        from src.rag.embeddings import fiche_to_text
        fiche = {
            "nom": "Master MIAGE",
            "etablissement": "Université de Tours",
            "ville": "Tours",
            "region": "Centre-Val de Loire",
            "niveau": "bac+5",
            "type_diplome": "Master",
        }
        out = fiche_to_text(fiche)
        assert out.startswith("Formation : Master MIAGE")
        assert "Établissement : Université de Tours" in out
        assert "Ville : Tours" in out
        assert "Région : Centre-Val de Loire" in out
        assert not out.startswith("[")

    def test_annexe_without_text_field_fallback_v4(self):
        """Edge case : fiche annexe sans champ `text` ou `text` trop court →
        bascule sur comportement v4 (parts joinés). Ne casse pas si data
        incomplète."""
        from src.rag.embeddings import fiche_to_text
        fiche = {
            "domain": "metier_prospective",
            "region": "Bretagne",
            # pas de text field
        }
        out = fiche_to_text(fiche)
        # Doit basculer sur fallback v4 (Formation : | Établissement : | ...)
        assert "Région : Bretagne" in out

    def test_annexe_with_too_short_text_fallback_v4(self):
        from src.rag.embeddings import fiche_to_text
        fiche = {
            "domain": "metier_prospective",
            "region": "Bretagne",
            "text": "Trop court",  # < 60 chars
        }
        out = fiche_to_text(fiche)
        # `Trop court` ne doit pas être utilisé tel quel comme embed principal
        assert not out.startswith("[metier_prospective]")

    def test_text_field_truncated_at_1500_chars(self):
        """Le champ `text` est tronqué à 1500 chars pour éviter dilution."""
        from src.rag.embeddings import fiche_to_text
        long_text = "x" * 3000  # 3000 chars
        fiche = {
            "domain": "metier_detail",
            "libelle_metier": "Test",
            "text": long_text,
        }
        out = fiche_to_text(fiche)
        # Le préfixe ajoute ~50 chars, mais le `text` est cappé à 1500
        # Donc total <= ~1600 chars
        assert len(out) <= 1600
        # Les 1500 premiers chars du text doivent être présents
        assert "x" * 1500 in out
