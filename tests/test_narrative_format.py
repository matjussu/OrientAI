"""Tests du routeur de forme déterministe (mode récit forme adaptative, ordre 1926).

Vérité terrain des formats T1-T9 = labels fournis par Jarvis dans l'ordre.
Le routeur étant marker-first sur le TEXTE, ces tests passent un profil minimal
(fallback) : ils isolent la couche déterministe (texte), pas l'extraction LLM.
La couche intent_type (départage) est testée séparément avec un profil porteur.
"""
from __future__ import annotations

import pytest

from src.agent.tools.profile_clarifier import Profile
from src.rag.narrative_format import (
    route_narrative_format,
    COMPARAISON, VALIDATION, TRAJECTOIRE, SHORTLIST, EXPLORATOIRE, CONSEIL,
    VALID_FORMATS,
)


def _p(intent_type="other", urgent=False, contraintes=None, a_eviter=None,
       mobilite=None, sector=None, confidence=0.8):
    """Profil minimal pour isoler la couche marqueurs (texte)."""
    return Profile(
        age_group="other_or_unknown", education_level="unknown",
        intent_type=intent_type, sector_interest=sector or [],
        region=None, urgent_concern=urgent, confidence=confidence,
        contraintes=contraintes or [], a_eviter=a_eviter or [], mobilite=mobilite,
    )


# --- Récits de test T1-T9 (texte inline = source de vérité Jarvis) ---

T1 = ("Je suis en terminale generale (spe maths et SES) a Toulouse, j'ai de bonnes notes "
      "un peu partout mais honnetement je n'ai aucune idee de ce que je veux faire apres le bac. "
      "J'aime bien comprendre comment marche l'economie et la societe, je suis assez a l'aise a "
      "l'oral, mais je ne me vois pas faire 5 ans d'etudes tres theoriques. Je voudrais rester "
      "dans le Sud si possible. Qu'est-ce qui pourrait me correspondre ?")

T2 = ("Je suis en terminale STMG a Lyon, admise sur Parcoursup a la fois en BUT GEA et en BTS "
      "Comptabilite-Gestion. Je n'arrive pas a choisir. Je veux travailler assez vite mais sans "
      "me fermer de portes si jamais je veux continuer en ecole apres. Lequel est le mieux pour moi ?")

T3 = ("Je suis en L2 de droit a Lille mais je m'ennuie et les debouches me font peur. J'avais "
      "pris l'option NSI au lycee et le code m'avait beaucoup plu. J'aimerais basculer vers le "
      "developpement ou la data, mais j'ai peur d'avoir perdu deux annees pour rien et mes parents "
      "s'inquietent pour le salaire. Je suis bloque a Lille. Comment je peux faire la transition ?")

T4 = ("Je suis en terminale generale avec les spes maths et NSI, j'ai 15 de moyenne, et je pense "
      "candidater en MIAGE apres une licence d'informatique. J'aime les maths appliquees et l'idee "
      "de faire le pont entre l'informatique et la gestion d'entreprise, mais je n'aime pas du tout "
      "le developpement web pur toute la journee. Est-ce que MIAGE c'est un bon choix pour mon profil ?")

T5 = ("Je suis en BTS SIO option SLAM a Nantes et je voudrais continuer en alternance dans le "
      "developpement, mais surtout pas dans le conseil ou la cybersecurite qui ne m'attirent pas. "
      "Je veux rester dans la region nantaise. Quelles ecoles ou licences pro en alternance vous me conseillez ?")

T6 = ("Je suis en terminale generale spe maths et physique a Rennes, j'ai un bon dossier. Je suis "
      "admis a la fois en prepa MPSI et en BUT Informatique, et je n'arrive vraiment pas a trancher. "
      "La prepa me fait un peu peur niveau rythme mais ca ouvre les ecoles d'inge, le BUT a l'air "
      "plus concret et plus court. Lequel correspond le mieux a quelqu'un qui veut devenir ingenieur sans se cramer ?")

T7 = ("Je suis en terminale generale avec les spes maths et SVT a Bordeaux, 16 de moyenne, et je "
      "veux faire une ecole d'ingenieur post-bac plutot dans le biomedical ou les biotechnologies. "
      "J'ai deja pas mal reflechi, je connais mon projet. Donne-moi juste les meilleures ecoles d'inge "
      "post-bac en bio/sante que je devrais viser, pas besoin de tout m'expliquer.")

T8 = ("Je suis en terminale techno STI2D pres de Clermont-Ferrand, je voudrais continuer dans "
      "l'informatique ou l'electronique. Le truc c'est que ma famille n'a pas les moyens, je ne peux "
      "pas payer une ecole privee a plusieurs milliers d'euros par an, il me faut absolument du public "
      "ou de l'alternance remuneree. Et je ne peux pas trop m'eloigner de la maison. Qu'est-ce qui est possible pour moi ?")

T9 = ("Je suis en premiere annee de licence d'eco-gestion a Montpellier et franchement je stresse a "
      "mort. J'ai l'impression de m'etre trompe, tout le monde autour de moi a l'air sur de soi et pas "
      "moi, j'ai peur de gacher mon annee et de decevoir mes parents. J'aime bien l'analyse de donnees "
      "et les langues mais je sais plus quoi en faire. Vous pouvez m'aider a y voir clair ?")


@pytest.mark.parametrize("recit,expected", [
    (T1, EXPLORATOIRE),
    (T2, COMPARAISON),
    (T3, TRAJECTOIRE),
    (T4, VALIDATION),
    (T5, CONSEIL),
    (T6, COMPARAISON),
    (T7, SHORTLIST),
])
def test_format_labels_T1_T7(recit, expected):
    d = route_narrative_format(_p(), recit)
    assert d.format == expected, f"attendu {expected}, obtenu {d.format} (matched={d.matched}, source={d.source})"
    assert d.is_valid()


def test_T8_anchor_constraint_on():
    """T8 : contrainte dure (pas les moyens / public obligatoire / pas mobile)."""
    d = route_narrative_format(_p(), T8)
    assert d.anchor_constraint is True
    assert d.constraint_terms, "doit lister les marqueurs de contrainte dure"
    # Base format : pas de lostness reelle (il a un domaine) -> CONSEIL via fallback.
    assert d.format in (CONSEIL, EXPLORATOIRE)


def test_T9_reassure_on_format_unaffected():
    """T9 : anxiete non-detresse -> reassure ON, format = exploratoire (lostness)."""
    d = route_narrative_format(_p(), T9)
    assert d.reassure is True
    assert d.format == EXPLORATOIRE  # reassure est un overlay, il ne change pas le format


def test_T5_no_anchor_soft_prefs():
    """T5 : alternance + region = preferences SOUPLES, pas un anchor dur."""
    d = route_narrative_format(_p(), T5)
    assert d.anchor_constraint is False


# --- Précédence multi-match (déterminisme en ambiguïté) ---

def test_precedence_comparaison_beats_exploratoire():
    txt = "je sais pas trop, BUT info ou prepa MPSI, lequel est le mieux pour moi ?"
    d = route_narrative_format(_p(), txt)
    assert d.format == COMPARAISON  # COMPARAISON > EXPLORATOIRE
    assert d.matched.get(EXPLORATOIRE)  # l'exploratoire a bien fire aussi


def test_precedence_validation_beats_trajectoire():
    txt = "est-ce que je devrais me reconvertir vers la data, est-ce un bon choix pour moi ?"
    d = route_narrative_format(_p(), txt)
    assert d.format == VALIDATION  # VALIDATION > TRAJECTOIRE
    assert d.matched.get(TRAJECTOIRE)


def test_precedence_trajectoire_beats_shortlist():
    txt = "je veux me reconvertir, donne-moi juste les meilleures formations data"
    d = route_narrative_format(_p(), txt)
    assert d.format == TRAJECTOIRE  # TRAJECTOIRE > SHORTLIST
    assert d.matched.get(SHORTLIST)


# --- intent_type en départage + fallback ---

def test_intent_type_tiebreak_when_no_markers():
    txt = "Bonjour, je vous ecris au sujet de mon avenir apres le bac, merci de votre aide."
    d = route_narrative_format(_p(intent_type="comparaison_options"), txt)
    assert d.format == COMPARAISON
    assert d.source == "intent_type"


def test_fallback_conseil_when_nothing():
    txt = "Bonjour, je vous ecris au sujet de mon avenir apres le bac, merci de votre aide."
    d = route_narrative_format(_p(intent_type="other"), txt)
    assert d.format == CONSEIL
    assert d.source == "fallback"


def test_fallback_profile_low_confidence_still_routes_by_text():
    """Même un profil de repli (confidence 0) route par le texte (déterministe)."""
    d = route_narrative_format(_p(intent_type="other", confidence=0.0), T2)
    assert d.format == COMPARAISON
    assert d.source == "markers"


def test_anchor_from_profile_fields():
    """L'anchor se déclenche aussi depuis les champs profil (pas que le texte)."""
    d = route_narrative_format(
        _p(contraintes=["je ne peux pas payer", "boursier"]),
        "je cherche une formation en informatique apres le bac",
    )
    assert d.anchor_constraint is True


def test_all_recits_return_valid_format():
    for txt in (T1, T2, T3, T4, T5, T6, T7, T8, T9):
        d = route_narrative_format(_p(), txt)
        assert d.format in VALID_FORMATS


# --- Frontière sécurité : reassure (anxiété) NE DOIT PAS escalader en détresse ---

def test_reassure_cases_do_not_trip_detresse_regex():
    """T9 + un R12-like (anxiété d'orientation normale) ne déclenchent AUCUN
    pattern urgent déterministe (contrôle négatif anti-sur-refus, symétrique R12).
    Le scope (détresse) est tranché en amont par scope_classifier — INCHANGÉ ici ;
    on prouve juste que la couche regex urgent ne sur-escalade pas ces cas."""
    from src.rag.scope_classifier import detect_urgent_signals_regex

    r12_like = ("Bonjour, je suis en terminale et je dois finaliser mes voeux Parcoursup. "
                "Je vais etre honnete, ca me stresse enormement, j'ai peur de faire le mauvais choix "
                "et de me fermer des portes. Vous pouvez m'aider a y voir clair ?")
    for txt in (T9, r12_like):
        assert detect_urgent_signals_regex(txt) == [], f"sur-escalade détresse sur: {txt[:50]}"
        # ces cas portent l'overlay reassure (anxiété), pas la détresse
        assert route_narrative_format(_p(urgent=True), txt).reassure is True


def test_real_detresse_phrases_still_escalate_regex():
    """Garde-fou symétrique : la vraie détresse déclenche bien le regex urgent
    (le filet R07 reste intact, scope_classifier non touché)."""
    from src.rag.scope_classifier import detect_urgent_signals_regex

    for txt in ("je tiens plus, j'en peux plus de tout ca",
                "je craque, rien n'a de sens pour moi"):
        assert detect_urgent_signals_regex(txt), f"détresse NON escaladée: {txt}"
