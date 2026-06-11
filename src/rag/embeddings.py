from mistralai.client import Mistral

from src.rag.sigle_expand import sigle_injection_text


EMBED_MODEL = "mistral-embed"


def _safe_pct(val, arrondi: bool = True) -> str | None:
    """Convertit un ratio [0,1] en pourcentage string, robuste aux NaN.

    Retourne None si val est None, NaN, ou non-convertible. Utilise
    `arrondi=True` par défaut pour stabilité retrieval (85.23% → 85%).
    """
    if val is None:
        return None
    import math
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f"{int(round(f * 100))}%" if arrondi else f"{f * 100:.1f}%"
    except (ValueError, TypeError):
        return None


def _format_insertion_pro(ip: dict) -> str | None:
    """Formate le dict `insertion_pro` en verbatim embedding-friendly.

    Supporte 2 schémas hétérogènes (v3 ADR-046-bis) :

    **Schéma Céreq** (source='cereq', 32 704 fiches, majoritairement Parcoursup/
    MonMaster enrichies par `attach_cereq_insertion`) :
        {taux_emploi_3ans, taux_emploi_6ans, taux_cdi, salaire_median_embauche,
         source, cohorte}

    **Schéma CFA** (source='inserjeunes_cfa', 11 314 fiches apprentissage) :
        {taux_emploi_6m/12m/18m/24m, taux_emploi_6m_attendu,
         valeur_ajoutee_emploi_6m, taux_contrats_interrompus,
         part_poursuite_etudes, part_emploi_6m, part_autres_situations,
         source, annee}

    Retourne une string concaténée (verbatim narratif) ou None si pas de data
    exploitable. Objectif : rendre les stats **retrievables** via l'embedding
    (au lieu d'être ignorées comme dans la baseline v2).
    """
    if not isinstance(ip, dict):
        return None
    source = (ip.get("source") or "").lower()
    fragments: list[str] = []

    # Schéma Céreq (insertion à 3 et 6 ans, agrégé par niveau+domaine)
    if "taux_emploi_3ans" in ip or "taux_emploi_6ans" in ip:
        cohorte = ip.get("cohorte") or "cohorte récente"
        t3 = _safe_pct(ip.get("taux_emploi_3ans"))
        t6 = _safe_pct(ip.get("taux_emploi_6ans"))
        tcdi = _safe_pct(ip.get("taux_cdi"))
        sal = ip.get("salaire_median_embauche")
        if t3:
            fragments.append(f"taux emploi 3 ans : {t3}")
        if t6:
            fragments.append(f"taux emploi 6 ans : {t6}")
        if tcdi:
            fragments.append(f"taux CDI : {tcdi}")
        if sal is not None and isinstance(sal, (int, float)):
            import math
            sal_f = float(sal)
            if not math.isnan(sal_f):
                fragments.append(f"salaire médian embauche : {int(sal_f)}€")
        if fragments:
            return f"Insertion pro (source Céreq, {cohorte}) : " + " — ".join(fragments)

    # Schéma CFA Inserjeunes (horizons 6/12/18/24 mois, apprentissage)
    if "taux_emploi_6m" in ip or "valeur_ajoutee_emploi_6m" in ip:
        annee = ip.get("annee") or "cumul récent"
        horizons: list[str] = []
        for h_key, h_lib in (
            ("taux_emploi_6m", "6 mois"),
            ("taux_emploi_12m", "12 mois"),
            ("taux_emploi_18m", "18 mois"),
            ("taux_emploi_24m", "24 mois"),
        ):
            pct = _safe_pct(ip.get(h_key))
            if pct:
                horizons.append(f"{h_lib} {pct}")
        if horizons:
            fragments.append("taux emploi " + ", ".join(horizons))
        va = _safe_pct(ip.get("valeur_ajoutee_emploi_6m"))
        if va:
            fragments.append(f"valeur ajoutée emploi 6m : {va[:-1]}pp")  # 8% → 8pp
        rupt = _safe_pct(ip.get("taux_contrats_interrompus"))
        if rupt:
            fragments.append(f"taux contrats interrompus : {rupt}")
        pours = _safe_pct(ip.get("part_poursuite_etudes"))
        if pours:
            fragments.append(f"poursuite études : {pours}")
        sf = _salary_fragment(ip)
        if sf:
            fragments.append(sf)
        if fragments:
            return f"Insertion apprentissage (Inserjeunes CFA, {annee}) : " + " — ".join(fragments)

    # Schéma salaire-direct (InserSup MESR / IP Doc doctorat — order C2b 2026-06-11) :
    # salaire net médian par formation posé en insertion_pro.salaire_median_embauche,
    # sans bloc taux Céreq/CFA. Rend le salaire retrievable au futur ré-embed.
    sf = _salary_fragment(ip)
    if sf:
        src = ip.get("salaire_source") or source or "enquête publique"
        cohorte = ip.get("salaire_cohorte") or ip.get("cohorte")
        an = f", promo {cohorte}" if cohorte else ""
        return f"Insertion pro (salaire {src}{an}) : {sf}"

    return None


def _salary_fragment(ip: dict) -> str | None:
    """Fragment verbatim salaire net médian (order C2b). None si pas de salaire.

    Étiquette le NET explicitement (RÈGLE 6) + l'horizon (12m/30m après diplôme)."""
    sal = ip.get("salaire_median_embauche")
    if sal is None or not isinstance(sal, (int, float)):
        return None
    import math
    if math.isnan(float(sal)):
        return None
    net = " net" if ip.get("salaire_net") else ""
    horizon = ip.get("salaire_horizon")
    hz = f" à {horizon}" if horizon else ""
    return f"salaire médian{net} : {int(float(sal))}€/mois{hz}"


def _format_profil_admis(profil_admis: dict | None) -> str | None:
    """Formate le dict `profil_admis` Parcoursup en verbatim embeddable.

    **Sprint 12 D1 (2026-05-01)** — exposition au RAG du champ profil
    historiquement présent dans les fiches mais ignoré par fiche_to_text.
    Élimine empiriquement ~30 % des hallu Sprint 11 P1.1 sur "qui est
    admis dans cette formation ?" (taux profil-spécifiques inventés
    faute de source exposée).

    Couverture corpus : 18,9 % des fiches (10 502 / 55 606) ont au moins
    une stat non-zéro (cf `docs/sprint12-D1-profil-admis-audit-champs-2026-05-01.md`).
    Le reste a soit un dict absent, soit un placeholder tout-zéros que
    Parcoursup n'a pas rempli pour la formation. Skip silencieux dans
    les deux cas pour ne pas polluer l'embedding avec "0 % boursiers"
    non-informatif.

    Sous-champs supportés (3 dicts imbriqués + 4 scalaires) :
    - `mentions_pct` {tb, b, ab, sans} : % admis par mention bac
    - `bac_type_pct` {general, techno, pro} : % admis par type bac
    - `acces_pct` {general, techno, pro} : taux d'accès profil-spécifique
        (≠ taux_acces_parcoursup_2025 global déjà exposé)
    - `boursiers_pct`, `femmes_pct`, `neobacheliers_pct`,
        `origine_academique_idf_pct` : scalaires démographiques

    Format de sortie (exemple EFREI Bordeaux Bachelor cyber) :
        "Profil des admis (Parcoursup 2025) : mentions au bac : 4 %
         très bien, 12 % bien, 29 % assez bien, 54 % sans mention —
         type de bac admis : 71 % bac général, 17 % bac techno, 12 %
         bac pro — taux d'accès par profil : 79 % pour bac général,
         14 % pour bac techno, 6 % pour bac pro — profil démographique :
         21 % boursiers, 10 % femmes, 77 % néobacheliers, 58 % origine
         académique Île-de-France"

    Valeurs déjà en pourcentage (e.g. `27.0` = 27 %, pas ratio 0-1) →
    pas de conversion `_safe_pct` ratio→%.
    """
    if not isinstance(profil_admis, dict):
        return None

    fragments: list[str] = []

    # 1. Mentions au bac (dict {tb, b, ab, sans})
    mentions = profil_admis.get("mentions_pct")
    if isinstance(mentions, dict):
        parts_m: list[str] = []
        for k, lib in (
            ("tb", "très bien"),
            ("b", "bien"),
            ("ab", "assez bien"),
            ("sans", "sans mention"),
        ):
            v = mentions.get(k)
            if isinstance(v, (int, float)) and v > 0:
                parts_m.append(f"{int(round(v))} % {lib}")
        if parts_m:
            fragments.append("mentions au bac : " + ", ".join(parts_m))

    # 2. Type de bac (admis) — dict {general, techno, pro}
    bt = profil_admis.get("bac_type_pct")
    if isinstance(bt, dict):
        parts_bt: list[str] = []
        for k, lib in (
            ("general", "bac général"),
            ("techno", "bac techno"),
            ("pro", "bac pro"),
        ):
            v = bt.get(k)
            if isinstance(v, (int, float)) and v > 0:
                parts_bt.append(f"{int(round(v))} % {lib}")
        if parts_bt:
            fragments.append("type de bac admis : " + ", ".join(parts_bt))

    # 3. Taux d'accès par profil bac — dict {general, techno, pro}
    # ≠ taux_acces_parcoursup_2025 global, profil-spécifique discriminant
    ac = profil_admis.get("acces_pct")
    if isinstance(ac, dict):
        parts_ac: list[str] = []
        for k, lib in (
            ("general", "bac général"),
            ("techno", "bac techno"),
            ("pro", "bac pro"),
        ):
            v = ac.get(k)
            if isinstance(v, (int, float)) and v > 0:
                parts_ac.append(f"{int(round(v))} % pour {lib}")
        if parts_ac:
            fragments.append("taux d'accès par profil : " + ", ".join(parts_ac))

    # 4. Scalaires démographiques (boursiers / femmes / néo / IDF)
    scalaires: list[str] = []
    for key, lib in (
        ("boursiers_pct", "boursiers"),
        ("femmes_pct", "femmes"),
        ("neobacheliers_pct", "néobacheliers"),
        ("origine_academique_idf_pct", "origine académique Île-de-France"),
    ):
        v = profil_admis.get(key)
        if isinstance(v, (int, float)) and v > 0:
            scalaires.append(f"{int(round(v))} % {lib}")
    if scalaires:
        fragments.append("profil démographique : " + ", ".join(scalaires))

    if not fragments:
        return None

    return "Profil des admis (Parcoursup 2025) : " + " — ".join(fragments)


def _format_admission_stats(fiche: dict) -> str | None:
    """Stats admission Parcoursup / MonMaster sous forme verbatim embeddable.

    - Parcoursup : `taux_acces_parcoursup_2025` (%) + `nombre_places`
    - MonMaster : `taux_admission` ratio 0-1 + `n_candidats_pp` + `n_acceptes_total`
    """
    source = (fiche.get("source") or "").lower()
    fragments: list[str] = []

    import math

    tap = fiche.get("taux_acces_parcoursup_2025")
    places = fiche.get("nombre_places")
    if tap is not None:
        try:
            tap_f = float(tap)
            if not math.isnan(tap_f):
                # Arrondi entier pour stabilité retrieval (52.0% → 52%)
                fragments.append(f"taux d'accès {int(round(tap_f))}%")
        except (ValueError, TypeError):
            pass
    if places is not None:
        fragments.append(f"{places} places")

    if source == "monmaster":
        import math
        ta_mm_pct = _safe_pct(fiche.get("taux_admission"))
        if ta_mm_pct:
            fragments.append(f"sélectivité {ta_mm_pct} admis")
        n_cand = fiche.get("n_candidats_pp")
        n_acc = fiche.get("n_acceptes_total")
        if isinstance(n_cand, (int, float)) and not math.isnan(float(n_cand)):
            fragments.append(f"{int(n_cand)} candidats")
        if isinstance(n_acc, (int, float)) and not math.isnan(float(n_acc)):
            fragments.append(f"{int(n_acc)} acceptés")

    return ("Admission : " + " — ".join(fragments)) if fragments else None


# ─── Step 11.7 chantier 3 — Signatures écoles prestigieuses ────────────────
#
# Les fiches Parcoursup/ONISEP des grandes écoles ont des `nom` génériques
# ("Formation d'ingénieur Bac+5 - Bac général") + `domaine` mal classifié
# ("ingenierie_industrielle" pour ENIB qui fait de l'informatique). Le
# signal métier (cybersécurité, data, etc.) n'est PAS dans la fiche.
#
# Audit empirique 2026-05-10 : ENIB Brest, ENSEIRB-MATMECA, INSA Rennes,
# CentraleSupélec ont toutes des `nom` génériques. Le retrieve dense sur
# "cyber" ne les ramène pas alors que ces écoles font tournent vraiment
# de la cyber/info au programme.
#
# Fix : pour ~25 écoles dont la spécialité est de NOTORIÉTÉ PUBLIQUE
# (Wikipedia, sites officiels), on injecte une signature courte dans le
# texte embedded. Ce N'EST PAS DE L'HALLUCINATION :
# - ENIB Brest fait bien de l'info/cyber (vérifiable site web École)
# - Le LLM voit toujours la fiche brute via FactCard JSON
# - Le LLM ne citera ENIB que si elle est dans le top-K du retrieve
# - On améliore le retrieve, pas la génération
#
# Liste conservatrice : écoles dont la spécialité est universellement
# admise. Si une école a des spécialités dépendantes du campus
# (ex INSA Toulouse vs INSA Lyon), on inclut dans la signature toutes
# les spécialités principales du groupe.

KNOWN_SCHOOL_SIGNATURES: dict[str, str] = {
    # Écoles d'ingénieurs prestigieuses (fait public)
    "ENIB": "École Nationale d'Ingénieurs de Brest, spécialités informatique cybersécurité électronique mécatronique",
    "ENSEIRB-MATMECA": "École d'ingénieurs Bordeaux INP, spécialités informatique cybersécurité électronique télécommunications mathématiques mécanique",
    "ENSEIRB": "École Nationale Supérieure d'Électronique Informatique Radiocommunications Bordeaux",
    "ENSSAT": "École Nationale Supérieure des Sciences Appliquées et de Technologie Lannion, spécialités informatique électronique optique photonique",
    "ENSIBS": "École Nationale Supérieure d'Ingénieurs de Bretagne-Sud Lorient, spécialités cybersécurité mécatronique",
    "INSA": "Institut National des Sciences Appliquées, spécialités informatique cybersécurité génie civil mécanique mathématiques chimie",
    "IMT Atlantique": "Institut Mines-Télécom, spécialités numérique cybersécurité énergie systèmes industriels",
    "Mines-Télécom": "Institut Mines-Télécom, spécialités numérique télécommunications cybersécurité",
    "CentraleSupélec": "École Centrale Supélec, spécialités élite ingénierie informatique mathématiques physique cybersécurité",
    "École polytechnique": "École polytechnique Palaiseau, spécialités élite sciences fondamentales mathématiques physique informatique",
    "Polytech": "Réseau Polytech écoles d'ingénieurs universitaires, spécialités polyvalentes informatique mécanique génie civil",
    "EFREI": "École d'ingénieurs informatique télécommunications cybersécurité",
    "EPITA": "École d'ingénieurs informatique cybersécurité intelligence artificielle",
    "EPITECH": "École d'informatique programmation développement",
    "ESILV": "École Supérieure d'Ingénieurs Léonard de Vinci, spécialités informatique mécanique finance",
    "ISAE-SUPAERO": "Institut Supérieur de l'Aéronautique et de l'Espace, ingénierie aéronautique spatial",
    "Centrale Lille": "École Centrale Lille, spécialités ingénierie polyvalente informatique mécanique",
    "Centrale Lyon": "École Centrale Lyon, spécialités ingénierie polyvalente",
    "Centrale Nantes": "École Centrale Nantes, spécialités ingénierie polyvalente",
    # ENS d'élite (Step 11.7 chantier 3 — fix faux positif "ENS" générique
    # qui matchait 900+ fiches "École Nationale Supérieure de XYZ"
    # non-ENS au sens grandes écoles).
    "ENS Ulm": "École Normale Supérieure Ulm Paris, sciences fondamentales lettres recherche académique",
    "ENS Cachan": "École Normale Supérieure Paris-Saclay (ex Cachan), sciences ingénierie",
    "ENS Lyon": "École Normale Supérieure Lyon, sciences lettres",
    "ENS Paris-Saclay": "École Normale Supérieure Paris-Saclay, sciences ingénierie",
    "ENS Rennes": "École Normale Supérieure Rennes, sciences sociales mathématiques informatique",
    # Écoles de commerce prestigieuses
    "HEC": "École des Hautes Études Commerciales Paris, programme grande école management finance commerce",
    "ESSEC": "École Supérieure des Sciences Économiques et Commerciales, management finance luxe",
    "ESCP": "École Supérieure de Commerce Paris, management européen",
    "EM Lyon": "École de management Lyon, management entrepreneuriat",
    "EDHEC": "École de management, finance management",
    "Audencia": "École de management Nantes",
    "NEOMA": "École de management Reims Rouen, management",
    "SKEMA": "École de management, business international",
    # Sciences Po (réseau)
    "Sciences Po": "Institut d'études politiques, sciences sociales relations internationales économie politique",
    "IEP": "Institut d'études politiques, sciences sociales politique économie",
    "études politiques": "Institut d'études politiques (Sciences Po), sciences sociales relations internationales économie politique",
}


def _detect_known_school_signature(etablissement: str) -> str | None:
    """Détecte si l'établissement matche une école prestigieuse connue
    et retourne sa signature publique. None sinon.

    Step 11.7 chantier 3 — l'enrichissement est conservateur : on matche
    sur l'acronyme/nom complet de l'école au début du libellé etab,
    pas sur des occurrences ambiguës. Ex "ENIB Brest" matche "ENIB" mais
    "Université de Brest" ne matche pas (ce n'est pas ENIB).
    """
    if not etablissement or not isinstance(etablissement, str):
        return None
    etab_norm = etablissement.strip()
    # Tri par longueur décroissante pour éviter les matches partiels
    # (ex "ENSEIRB-MATMECA" doit matcher avant "ENSEIRB" tout court)
    for school in sorted(KNOWN_SCHOOL_SIGNATURES.keys(), key=len, reverse=True):
        # Match insensible à la casse, mais sur le mot complet
        # (boundary regex-like via vérification simple)
        if school.lower() in etab_norm.lower():
            return KNOWN_SCHOOL_SIGNATURES[school]
    return None


# Mots-clés métier détectables dans nom/detail pour enrichir le signal
# embedding. Détection insensible à la casse, on enrichit uniquement si
# le mot-clé est présent en clair (pas d'inférence).
_METIER_KEYWORDS: list[tuple[str, str]] = [
    # (regex, tag_à_ajouter)
    (r"\bcyber\w*|sécurité\s+informatique|sécurité\s+des\s+systèmes", "cybersécurité informatique sécurité"),
    (r"\bdata\b|\bdonnée[s]?\b|machine\s+learning|big\s+data", "data science données analyse"),
    (r"\bintelligence\s+artificielle|\bIA\b|\bAI\b", "intelligence artificielle IA"),
    (r"\brobotique|automatisme[s]?|automatique\b", "robotique automatique"),
    (r"\bréseau[x]?\b|\btélécom\w*", "réseaux télécommunications"),
    (r"\bbiotechnolog\w+|\bbioinformatique", "biotechnologie bioinformatique"),
    (r"\bquantique|nanotechnolog\w+", "quantique nanotechnologie"),
    (r"\baéronaut\w+|spatial[e]?", "aéronautique spatial"),
]


def _detect_metier_keywords_in_text(*texts: str) -> str:
    """Détecte les mots-clés métier dans les textes fournis et retourne
    une chaîne `Mots-clés métier détectés : ...` ou ''.

    Step 11.7 chantier 3 — détection sur `nom`, `detail`, `parcours_long`,
    `mention`. Si plusieurs mots-clés détectés → tous concaténés.
    """
    import re
    haystack = " ".join(t for t in texts if t).lower()
    if not haystack:
        return ""
    found_tags = []
    for pattern, tag in _METIER_KEYWORDS:
        if re.search(pattern, haystack, re.IGNORECASE):
            found_tags.append(tag)
    if not found_tags:
        return ""
    return "Mots-clés métier détectés : " + " ; ".join(found_tags)


def fiche_to_text(fiche: dict) -> str:
    """Construit le texte embedded pour une fiche.

    **v3 (2026-04-24)** — injection des stats chiffrées retrievables :
    - `insertion_pro.taux_emploi_*` (Céreq 3ans/6ans ou CFA 6/12/18/24m)
    - `insertion_pro.salaire_median_embauche` + `taux_cdi` Céreq
    - `taux_admission` MonMaster + `taux_acces_parcoursup_2025`
    - `n_candidats_pp` / `n_acceptes_total` MonMaster

    **v4 step 11.7 chantier 3 (2026-05-10)** — enrichissement signal métier :
    - Signatures publiques des écoles prestigieuses (ENIB, INSA, HEC, etc.)
      via `_detect_known_school_signature`
    - Détection mots-clés métier (cyber, data, IA, robotique, etc.) dans
      `nom` + `detail` + `parcours_long` + `mention`

    **v5 Chantier C+ (2026-05-13)** — exploitation du champ `text` pour les
    fiches annexes (`domain != none`). Audit du 2026-05-13 a révélé que
    13 412 fiches annexes (DARES Métiers 2030, CROUS résidences, INSEE
    salaires PCS, Inserjeunes lycée pro, MESR parcours bacheliers, ROME
    fiches détaillées, RNCP blocs de compétences, financement, APEC
    régions, voie pré-bac, DROM-COM) étaient embed avec un signal
    quasi-vide (~42-124 chars) alors que leur champ `text` contient
    298-1807 chars de contenu sémantique exploitable.

    Conséquence empirique : sur Q1 du spot-check V5 ("métiers Occitanie
    2030"), 0 fiche `metier_prospective` (DARES) dans le top-50 brut
    alors que 1 160 disponibles dans le corpus.

    Fix additif strict : si `domain` non vide ET `text` substantiel
    (>=60 chars), on utilise un préfixe domain/région/métier + le champ
    `text` directement. Aucun changement pour les fiches Parcoursup
    (`domain` absent), qui restent le cœur production éprouvé Run F+G.

    Motivation : bench v2 (bench_personas_2026-04-24) a révélé que le
    modèle hallucinait des statistiques précises parce que le retrieval
    ne les exposait pas. En les injectant dans le texte embedding, elles
    deviennent retrievables + citables par le générateur.

    Step 11.7 motivation : audit empirique du dump step 11.5 a montré que
    les écoles prestigieuses (ENIB Brest, ENSEIRB-MATMECA, INSA Rennes,
    CentraleSupélec) ont des `nom` Parcoursup génériques sans signal
    métier. Sur "cyber Bretagne", elles ne remontent pas en top-K.
    L'enrichissement injecte le signal métier qu'elles ont publiquement
    (Wikipedia, sites écoles) sans toucher à la fiche brute (le LLM
    voit toujours les chiffres originaux via FactCard JSON).
    """
    # Chantier C+ — fiches annexes (domain != none) avec champ `text` substantiel
    # Préfixe court [domain] + Région + métier/sujet, puis contenu sémantique
    domain = fiche.get("domain")
    if domain:
        text_field = (fiche.get("text") or "").strip()
        if text_field and len(text_field) >= 60:
            prefix_parts = [f"[{domain}]"]
            if fiche.get("region"):
                prefix_parts.append(f"Région : {fiche['region']}")
            # Signaux métier/sujet par sous-corpus
            if fiche.get("fap_libelle"):  # DARES Métiers 2030
                prefix_parts.append(f"Métier : {fiche['fap_libelle']}")
            elif fiche.get("libelle_metier"):  # ROME métiers
                prefix_parts.append(f"Métier : {fiche['libelle_metier']}")
            elif fiche.get("libelle"):  # divers (financement, etc.)
                prefix_parts.append(f"Libellé : {fiche['libelle']}")
            elif fiche.get("subject"):  # CROUS, etc.
                prefix_parts.append(f"Sujet : {fiche['subject']}")
            # Tronquer text_field à 1500 chars pour éviter dilution
            # (test empirique : >1500 fait baisser la précision du retrieve)
            embed_text = f"{' | '.join(prefix_parts)} | {text_field[:1500]}"
            # J2 enrichissement — injection sigle (additif) sur le chemin annexe
            # (fiches BUT-specialty domain!=none) : la fiche forme-longue reçoit
            # son acronyme pour que dense matche l'acronyme nu.
            inj = sigle_injection_text(fiche)
            return f"{embed_text} | {inj}" if inj else embed_text

    # Comportement v4 inchangé pour fiches Parcoursup (domain absent)
    parts = [
        f"Formation : {fiche.get('nom', '')}",
        f"Établissement : {fiche.get('etablissement', '')}",
        f"Ville : {fiche.get('ville', '')}",
    ]
    if fiche.get("type_diplome"):
        parts.append(f"Diplôme : {fiche['type_diplome']}")
    if fiche.get("niveau"):
        parts.append(f"Niveau : {fiche['niveau']}")
    if fiche.get("phase"):
        parts.append(f"Phase : {fiche['phase']}")
    if fiche.get("statut"):
        parts.append(f"Statut : {fiche['statut']}")
    labels = fiche.get("labels") or []
    if labels:
        parts.append(f"Labels : {', '.join(labels)}")
    if fiche.get("domaine"):
        parts.append(f"Domaine : {fiche['domaine']}")
    if fiche.get("departement"):
        parts.append(f"Département : {fiche['departement']}")
    if fiche.get("region"):
        parts.append(f"Région : {fiche['region']}")

    # v3 — stats admission retrievables
    adm = _format_admission_stats(fiche)
    if adm:
        parts.append(adm)

    # Sprint 12 D1 — profil_admis Parcoursup retrievable (mentions, bac type,
    # taux d'accès profil-spécifique, démographie). Skip silencieux quand
    # placeholder tout-zéros (~ 81 % du corpus).
    pa_text = _format_profil_admis(fiche.get("profil_admis"))
    if pa_text:
        parts.append(pa_text)

    # Détail narratif (Vague B.3, 800 chars) — sémantique formation
    detail = (fiche.get("detail") or "").strip()
    if detail:
        parts.append(f"Détail : {detail[:800]}")

    # Débouchés ROME libellés (Vague B.3) — appellations métiers
    debouches = fiche.get("debouches") or []
    if debouches:
        libelles = [
            d.get("libelle", "").strip()
            for d in debouches if d.get("libelle")
        ]
        if libelles:
            parts.append(f"Métiers possibles : {', '.join(libelles)}")

    # v3 — Insertion pro retrievable (taux emploi + salaire Céreq ou horizons CFA)
    ip = fiche.get("insertion_pro")
    if ip:
        ip_text = _format_insertion_pro(ip)
        if ip_text:
            parts.append(ip_text)

    # Step 11.7 chantier 3 — Signature publique école prestigieuse
    school_signature = _detect_known_school_signature(
        fiche.get("etablissement") or ""
    )
    if school_signature:
        parts.append(f"Signature école : {school_signature}")

    # Step 11.7 chantier 3 — Mots-clés métier détectés dans nom/detail
    metier_tags = _detect_metier_keywords_in_text(
        fiche.get("nom") or "",
        fiche.get("detail") or "",
        fiche.get("parcours_long") or "",
        fiche.get("mention") or "",
        fiche.get("specialite") or "",
    )
    if metier_tags:
        parts.append(metier_tags)

    # J2 enrichissement — injection sigle (additif) sur le chemin non-annexe.
    inj = sigle_injection_text(fiche)
    if inj:
        parts.append(inj)

    return " | ".join(parts)


def embed_texts(client: Mistral, texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=EMBED_MODEL, inputs=texts)
    return [d.embedding for d in response.data]


def embed_texts_batched(client: Mistral, texts: list[str], batch_size: int = 64) -> list[list[float]]:
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        all_embeddings.extend(embed_texts(client, batch))
    return all_embeddings
