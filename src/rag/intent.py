"""Rule-based intent classifier for student questions.

Maps a French orientation question to one of 7 intent classes. The
intent then drives a retrieval strategy (top_k_sources, mmr_lambda)
via intent_to_config().

Why rule-based: deterministic, zero API cost, auditable in the study
report. The 7 classes map cleanly to observable surface patterns
(comparison particles, geographic NER, grade mentions, etc.).

Order matters in classify_intent — checks are done from most specific
to least specific, with general as the catch-all fallback.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


INTENT_COMPARAISON = "comparaison"
INTENT_GEOGRAPHIC = "geographic"
INTENT_REALISME = "realisme"
INTENT_PASSERELLES = "passerelles"
INTENT_DECOUVERTE = "decouverte"
INTENT_CONCEPTUAL = "conceptual"
INTENT_GENERAL = "general"

# Chantier 2 (2026-05-03) — questions factuelles pointues sur une formation
# nommée. Quand détecté ET entité reconnue ET fuzzy_score ≥ 85 → bypass RAG
# via SELECT structuré sur formations.json (cf src/lookup/structured_select).
# Sinon (ambigu, multi-match, confidence basse) → fallback RAG normal.
# Argument démo INRIA : « les chiffres viennent toujours d'un lookup, jamais
# d'une génération. Zéro hallu chiffres par construction. »
INTENT_FACTUAL_POINTED = "factual_pointed"


# --- ADR-049 : domain hints orthogonaux (multi-corpus reranker) ---
# Hints additifs (parallèles aux INTENT_*) qui détectent quand une query
# devrait privilégier un corpus retrievable non-formation. None par défaut
# (= comportement formation-centric inchangé). Le reranker applique un
# boost UNIQUEMENT aux fiches dont `domain` matche le hint.
DOMAIN_HINT_METIER = "metier"
DOMAIN_HINT_PARCOURS = "parcours_bacheliers"
DOMAIN_HINT_APEC = "apec_region"
DOMAIN_HINT_CROUS = "crous"
DOMAIN_HINT_INSEE_SALAIRE = "insee_salaire"
DOMAIN_HINT_INSERTION_PRO = "insertion_pro"
DOMAIN_HINT_METIER_PROSPECTIVE = "metier_prospective"  # DARES Métiers 2030
DOMAIN_HINT_COMPETENCES_CERTIF = "competences_certif"  # France Comp blocs RNCP
# Sprint 6 axes (Sprint 7 Action 5 : tuner intent classifier)
DOMAIN_HINT_FORMATION_INSERTION = "formation_insertion"  # Inserjeunes lycée pro (axe 3b)
DOMAIN_HINT_FINANCEMENT_ETUDES = "financement_etudes"  # Financement curé (axe 4)
DOMAIN_HINT_TERRITOIRE_DROM = "territoire_drom"  # DROM-COM territorial (axe 2)
DOMAIN_HINT_VOIE_PRE_BAC = "voie_pre_bac"  # BAC PRO + CAP catalogue (axe 3a)
# Vague 3.4 (2026-05-08) — Calendrier Parcoursup/MonMaster (gap mesuré recall@5=0%)
DOMAIN_HINT_CALENDRIER = "calendrier"


@dataclass(frozen=True)
class IntentConfig:
    top_k_sources: int
    mmr_lambda: float


_CONFIGS: dict[str, IntentConfig] = {
    INTENT_GENERAL:     IntentConfig(top_k_sources=10, mmr_lambda=0.7),
    INTENT_COMPARAISON: IntentConfig(top_k_sources=12, mmr_lambda=0.6),
    INTENT_GEOGRAPHIC:  IntentConfig(top_k_sources=12, mmr_lambda=0.4),
    INTENT_REALISME:    IntentConfig(top_k_sources=6,  mmr_lambda=0.85),
    INTENT_PASSERELLES: IntentConfig(top_k_sources=10, mmr_lambda=0.6),
    INTENT_DECOUVERTE:  IntentConfig(top_k_sources=12, mmr_lambda=0.3),
    INTENT_CONCEPTUAL:  IntentConfig(top_k_sources=4,  mmr_lambda=0.9),
    # factual_pointed bypasse normalement le RAG (SELECT structuré).
    # Mais si le SELECT échoue (entité ambiguë, fuzzy<85, field absent),
    # fallback RAG avec top-k réduit (3-5) et MMR forte (la question
    # cible une seule formation, pas besoin de diversité).
    INTENT_FACTUAL_POINTED: IntentConfig(top_k_sources=5, mmr_lambda=0.9),
}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


_FRENCH_CITIES = {
    "paris", "lyon", "marseille", "toulouse", "nice", "nantes", "strasbourg",
    "montpellier", "bordeaux", "lille", "rennes", "reims", "saint-etienne",
    "toulon", "grenoble", "dijon", "angers", "nimes", "villeurbanne",
    "aix-en-provence", "brest", "le mans", "amiens", "tours", "limoges",
    "clermont-ferrand", "besancon", "metz", "perpignan", "orleans",
    "mulhouse", "rouen", "caen", "nancy", "argenteuil", "boulogne-billancourt",
    "saint-denis", "vannes", "lorient", "quimper", "la rochelle", "pau",
    "valence", "annecy", "chambery", "poitiers", "avignon", "calais",
    "dunkerque", "le havre", "saint-nazaire",
}
_FRENCH_REGIONS = {
    "bretagne", "normandie", "alsace", "lorraine", "provence", "occitanie",
    "aquitaine", "auvergne", "bourgogne", "champagne", "franche-comte",
    "ile-de-france", "nord", "picardie", "pays de la loire", "rhone-alpes",
    "centre", "limousin", "poitou", "languedoc", "corse", "midi-pyrenees",
}


_PATTERNS_COMPARAISON_NORM = [
    re.compile(r"\bcompar(e[rz]?|aison)\b"),
    re.compile(r"\bdifferenc[a-z]*\s+entre\b"),
    re.compile(r"\bvaut[\s-]il\s+mieux\b"),
    re.compile(r"\bplutot que\b"),
    re.compile(r"\bmieux\s+(?:que|entre)\b"),
]


# Chantier 2 (2026-05-03) — patterns questions factuelles pointues.
# La question demande UN chiffre/fait précis sur UNE formation/école nommée.
# Si match → SELECT structuré (lookup déterministe, zero hallu chiffres).
# Patterns conservatifs : doit explicitement mentionner un champ chiffré
# (taux, sélectivité, salaire, places, frais, etc.) ET ressembler à une
# question pointue (pas une demande d'orientation générale).
_PATTERNS_FACTUAL_POINTED = [
    # "Quel est le taux d'accès de [formation]"
    re.compile(r"\bquel(?:le)?\s+(?:est\s+)?(?:le\s+)?(?:taux|pourcentage)\s+(?:d['e]\s*)?(?:acces|admission|reussite|insertion|emploi|cdi)"),
    # "C'est quoi la sélectivité de X"
    re.compile(r"\b(?:c['e]\s*est\s+quoi|quel(?:le)?\s+est)\s+(?:la\s+)?(?:selectivit|tension|cote)"),
    # "Combien de places à X"
    re.compile(r"\bcombien\s+(?:de\s+)?places?\b"),
    # "Combien de candidats X"
    re.compile(r"\bcombien\s+(?:de\s+)?(?:candidat|voeux|inscrit)"),
    # "Quel salaire après X" (formation nommée, pas générique)
    re.compile(r"\b(?:quel\s+(?:est\s+)?(?:le\s+)?)?salaire\s+(?:median|moyen|annuel|net|brut|de\s+(?:sortie|debut))"),
    # "Combien gagne un sortant X"
    re.compile(r"\bcombien\s+gagne\b"),
    # "Quels frais à X" / "Coût de X"
    re.compile(r"\b(?:quel(?:s|les)?\s+(?:sont\s+(?:les\s+)?)?|combien\s+coute|cout\s+(?:de\s+(?:la|l['e]\s*))?)?\s*(?:frais|cout|tarif|cotisation)\s+(?:de|d['e]\s*|annuel)"),
    # "Le taux de X est-il" / "Quel est le X de la formation Y"
    re.compile(r"\b(?:taux|nombre)\s+(?:de\s+|d['e]\s*)?[a-z]+\s+(?:est|de\s+(?:la|l['e]\s*))"),
    # Questions formelles "X taux d'accès", "Y sélectivité 2025"
    re.compile(r"\btaux\s+d['e]\s*(?:acces|admission|reussite|insertion|emploi|cdi)\s+(?:pour|de|d['e]\s*|du|au)"),
]
# Detected on the ORIGINAL question (case-sensitive) — catches the
# "EPITA ou EPITECH" / "INSA et CENTRALE" pattern where both sides
# are named institutions written as acronyms.
_PATTERNS_COMPARAISON_RAW = [
    re.compile(r"\b[A-Z][A-Z\-]{2,}\s+(?:ou|et)\s+[A-Z][A-Z\-]{2,}\b"),
]

_PATTERNS_REALISME = [
    re.compile(r"\b\d{1,2}[,.]?\d?\s+de\s+moyenne\b"),
    re.compile(r"\bavec\s+\d{1,2}\b"),
    re.compile(r"\btaux\s+(?:d['e]\s*)?(?:admission|acceptation|reussite)\b"),
    re.compile(r"\bselectivit[a-z]*\b"),
    re.compile(r"\baccessib[a-z]*\b"),
    re.compile(r"\b(?:est-ce que je peux|ai-je une chance|suis-je accept[a-z]+|puis-je integrer)\b"),
    re.compile(r"\bdossier\s+(?:moyen|faible|bon)\b"),
]

_PATTERNS_PASSERELLES = [
    re.compile(r"\breorient[a-z]*\b"),
    re.compile(r"\breconvers[a-z]*\b"),
    re.compile(r"\bpasserelle[sx]?\b"),
    re.compile(r"\bchanger\s+de\s+(?:filiere|voie|domaine|orientation)\b"),
    re.compile(r"\bapres\s+(?:mon|mes|\d)\s+(?:ans?|annee)"),
    re.compile(r"\btransition\s+(?:vers|professionnelle)\b"),
]

_PATTERNS_DECOUVERTE = [
    re.compile(r"\bquels metiers\b"),
    re.compile(r"\bdecouvr[a-z]*\b"),
    re.compile(r"\bmeconnu[sx]?\b"),
    re.compile(r"\boriginal[a-z]*\b"),
    re.compile(r"\bpiste[sx]?\b"),
    re.compile(r"\bj['e]\s*aime\b"),
    re.compile(r"\bje\s+(?:suis\s+)?(?:curieu[xs]|interess[a-z]+|passionn[a-z]+)\b"),
    re.compile(r"\bje\s+m['e]\s*interesse\s+(?:a|au|aux)\b"),
    re.compile(r"\bpropose[\-z]?[\-z]?moi\b"),
]

_PATTERNS_CONCEPTUAL = [
    re.compile(r"\bc['e]\s*est\s+quoi\b"),
    re.compile(r"\bqu['e]\s*est-ce\b"),
    re.compile(r"\bcomment\s+fonctionne\b"),
    re.compile(r"\bexpli(?:que[rz]?|cation)\b"),
    re.compile(r"\bdefini(?:tion|s|r)\b"),
]


# --- ADR-049 : patterns domain hint multi-corpus ---

# APEC : marché du travail cadres régional. Priorité 1 (le plus spécifique,
# évite que "marché du travail" matche aussi sur metier).
_PATTERNS_DOMAIN_APEC = [
    re.compile(r"\bmarche\s+(?:du\s+)?(?:travail|emploi)\b"),
    re.compile(r"\brecrutement[sx]?\s+(?:des\s+)?cadre[sx]?\b"),
    re.compile(r"\bcadre[sx]?\s+(?:en|a|au)\s+\d{4}\b"),
    re.compile(r"\bsalaire[sx]?\s+(?:median[a-z]*\s+)?cadre[sx]?\b"),
    re.compile(r"\bdynami(?:sme|que[sx]?)\s+(?:des\s+)?cadre[sx]?\b"),
    re.compile(r"\bperspective[sx]?\s+cadre[sx]?\b"),
    re.compile(r"\bobservatoire\s+(?:de\s+l['e]\s*emploi|des\s+cadre)"),
    re.compile(r"\bregion[a-z]*\s+(?:la\s+plus\s+)?dynami"),
]

# Parcours bacheliers : taux de réussite licence / passage L1→L2 /
# redoublement / réorientation DUT-BUT par profil bachelier.
_PATTERNS_DOMAIN_PARCOURS = [
    re.compile(r"\btaux\s+(?:de\s+)?(?:reussite|passage|obtention)\s+(?:en\s+)?(?:licence|l1|l2)"),
    re.compile(r"\bpassage\s+(?:en\s+)?l[12]\b"),
    re.compile(r"\bredoublement\s+(?:en\s+)?l1\b"),
    re.compile(r"\breorientation\s+(?:en\s+)?(?:dut|but)\b"),
    re.compile(r"\bobtention\s+(?:de\s+la\s+)?licence\s+en\s+\d\s+ans?\b"),
    re.compile(r"\b(?:bac|bachelier)\s+(?:l|s|es|stmg|techno|pro)[a-z]*\s+mention"),
    re.compile(r"\bcohorte[sx]?\s+(?:de\s+)?bacheliers?\b"),
    re.compile(r"\bstats?\s+(?:dis|des)?ent.*licence"),
]

# Métier : profession / "que fait un X" / "devenir X" / "rôle de".
# Évite que "marché du travail" + "cadres" matche aussi (priorité APEC).
_PATTERNS_DOMAIN_METIER = [
    re.compile(r"\bque\s+fait\s+un[e]?\b"),
    re.compile(r"\brole\s+(?:d['e]\s*un[e]?|du)\b"),
    re.compile(r"\bquel(?:le)?\s+(?:est\s+)?(?:le\s+)?metier\b"),
    re.compile(r"\bentre\s+(?:le[s]?\s+)?metier[sx]?\b"),
    re.compile(r"\b(?:devenir|etre)\s+(?:developpeu[rs]|ingenieur[s]?|actuair|infirmier|medecin|architect|psychologue|kine|avocat|comptable|enseignant|professeur|chercheur|consultant|journalist|designer|chef|technicien)"),
    re.compile(r"\bmetier[sx]?\s+(?:artistique[sx]?|manuel[sx]?|technique[sx]?|de\s+(?:bouche|terrain|service))"),
    re.compile(r"\b(?:profession|carriere)\s+(?:de|en|d['e]\s*)"),
    re.compile(r"\bjob\s+(?:de|d['e]\s*)"),
    re.compile(r"\bworking?\s+with\s+my\s+hands\b"),
    re.compile(r"\btravailler\s+(?:de\s+mes\s+|de\s+ses\s+)?mains\b"),
]


# Vague 3.4 (2026-05-08) — Calendrier Parcoursup/MonMaster + DSE CROUS.
# Patterns ciblant les questions calendaires : "quand", "date", "phase",
# "calendrier", "ouverture", "fermeture vœux", etc. Combiné avec les
# plateformes Parcoursup/MonMaster/DSE/CROUS pour discriminer.
_PATTERNS_DOMAIN_CALENDRIER = [
    # Question "quand" + plateforme
    re.compile(r"\bquand\s+.*?(parcoursup|monmaster|master|voeux|admission|inscription|phase)\b"),
    re.compile(r"\b(?:parcoursup|monmaster).*?(quand|date|calendrier|phase)\b"),
    # Date limite / deadline
    re.compile(r"\bdate\s+(?:limite|de\s+(?:cloture|fin))\b"),
    re.compile(r"\bderniere\s+(?:date|echeance|deadline)\b"),
    re.compile(r"\bechean[cs]e[sx]?\b"),
    # Phases Parcoursup
    re.compile(r"\bphase\s+(?:complementaire|principale|admission|reception)\b"),
    re.compile(r"\b(?:ouverture|fermeture)\s+(?:de\s+)?(?:la\s+)?(?:plateforme|inscriptions?|voeux)\b"),
    # Calendrier explicite
    re.compile(r"\bcalendrier\s+(?:parcoursup|monmaster|master|admission|voeux|2026|dse|crous|bourse)\b"),
    # Voeux + temporel
    re.compile(r"\b(?:formuler|saisir|valider|confirmer)\s+(?:les?\s+)?voeux\b"),
    # Résultats / réponses Parcoursup
    re.compile(r"\bresultat[sx]?\s+(?:parcoursup|admission|monmaster)\b"),
    re.compile(r"\breponse[sx]?\s+(?:parcoursup|formation[sx]?|admission)\b"),
    # MonMaster spécifique
    re.compile(r"\bmonmaster\b.*?(date|calendrier|phase|candidature[sx]?)"),
    re.compile(r"\bcandidatures?\s+master[sx]?\b"),
    # Vague 3.4+ — DSE / Bourse / Logement CROUS (temporel uniquement,
    # sinon "logement CROUS Lyon" → CROUS hint pour les questions de prix)
    re.compile(r"\bquand\s+.*?(dse|dossier\s+social|bourse|logement\s+(?:crous|etudiant))\b"),
    re.compile(r"\b(?:dse|dossier\s+social\s+etudiant)\s+.*?(quand|date|calendrier|2026|ouverture|fermeture|deadline|delai|periode)\b"),
    re.compile(r"\b(?:bourse|logement)\s+crous\s+.*?(quand|date|calendrier|2026|delai|deadline|fermeture|periode)\b"),
    re.compile(r"\b(?:date|calendrier|periode)\s+.*?(dse|bourse\s+crous|logement\s+crous|dossier\s+social)\b"),
    # Demande bourse/logement (intention temporelle implicite : "comment faire")
    # Déterminants français étendus (un/une/le/la/son/sa/mon/ma/du/de la)
    re.compile(r"\bcomment\s+(?:demander|faire|remplir|constituer)\s+(?:un[e]?|le|la|son|sa|mon|ma|du)\s+(?:dse|dossier\s+social|bourse|logement\s+crous)\b"),
    # Saisie vœux logement — gère ligature œ ET version normalisée oe
    re.compile(r"\b(?:saisir|saisie)\s+(?:les\s+)?(?:voeux|vœux)\s+(?:de\s+)?logement\b"),
    # Attribution logement CROUS
    re.compile(r"\bcycle\s+d['e]?\s*attribution\s+(?:logement|crous)"),
    re.compile(r"\battribution\s+(?:de[sx]?\s+)?logement[sx]?\s+(?:crous|universitaire)"),
]


# Phase B (ordre 2026-04-25-1442) : 3 nouveaux domains aggregés
_PATTERNS_DOMAIN_CROUS = [
    re.compile(r"\bcrous\b"),
    re.compile(r"\blogement[sx]?\s+(?:etudiant|universitaire|crous)\b"),
    re.compile(r"\bresidence[sx]?\s+(?:universitaire|crous|etudiante[sx]?)\b"),
    re.compile(r"\b(?:resto[sx]?|restaurant[sx]?|cafeteri[as]+)\s+(?:u[r]?|universitaire[sx]?|crous)\b"),
    re.compile(r"\bvie\s+etudiante\b"),
    re.compile(r"\bse\s+loger\s+(?:a|en|pour)\s+(?:l[ae]?|mes?)\s*(?:fac|etude|universite)"),
    re.compile(r"\bou\s+(?:se\s+)?loger\s+(?:a|en|pendant)\s+(?:les\s+)?etude[sx]?\b"),
]

_PATTERNS_DOMAIN_INSEE_SALAIRE = [
    re.compile(r"\bsalaire[sx]?\s+(?:median[a-z]*|moyen[a-z]*|annuel[a-z]*|net[a-z]*|brut[a-z]*)\b"),
    re.compile(r"\bcombien\s+gagne[a-z]*\s+un[e]?\b"),
    re.compile(r"\bremuneration[sx]?\s+(?:median[a-z]*|moyenn[a-z]*)\b"),
    re.compile(r"\bsalaire[sx]?\s+(?:par|selon|tranche)\s+(?:age|tranche)\b"),
    re.compile(r"\bsalaire[sx]?\s+(?:cadre[sx]?|professions?\s+intermediaires?|employes?|ouvriers?)\b"),
    re.compile(r"\bgrille\s+(?:de\s+)?salaire[sx]?\b"),
    re.compile(r"\bpcs\s+(?:21|22|23|31|34|35|37|54)\b"),
    re.compile(r"\binsee\s+(?:salaan|salaires?)\b"),
]

_PATTERNS_DOMAIN_INSERTION_PRO = [
    re.compile(r"\btaux\s+(?:d['e]\s*)?(?:insertion|emploi)\s+(?:a|apres|au\s+bout)\s+(?:de\s+)?(?:6|12|18|24|30)\s+mois\b"),
    re.compile(r"\binsertion\s+professionnel[a-z]+\s+(?:apres|post)\s+(?:master|licence|diplom)"),
    re.compile(r"\b(?:debouches?|insertion)\s+(?:a|apres)\s+(?:bac\s*\+\s*[35]|master|licence)\b"),
    re.compile(r"\btrouve[a-z]*\s+(?:un\s+)?(?:emploi|travail)\s+(?:apres|post|au\s+bout\s+de)"),
    re.compile(r"\bcombien\s+(?:de\s+temps\s+)?(?:pour\s+)?trouver\s+(?:un\s+)?emploi\b"),
    re.compile(r"\bsortants?\s+(?:de\s+)?master\b"),
    re.compile(r"\binsersup\b"),
    re.compile(r"\benquete\s+insertion\b"),
]


# DARES Métiers 2030 — projections recrutement par FAP
_PATTERNS_DOMAIN_METIER_PROSPECTIVE = [
    re.compile(r"\bmetier[sx]?\s+(?:en\s+)?2030\b"),
    re.compile(r"\bperspective[sx]?\s+(?:de\s+)?(?:recrutement|emploi)\b"),
    re.compile(r"\b(?:projection|prevision)[sx]?\s+(?:de\s+)?(?:recrutement|emploi|metier)"),
    re.compile(r"\bpostes?\s+a\s+pourvoir\b"),
    re.compile(r"\b(?:dares|projection\s+dares)\b"),
    re.compile(r"\bquels?\s+metiers?\s+(?:vont\s+)?recruter\b"),
    re.compile(r"\b(?:depart[sx]?\s+(?:en\s+)?(?:fin\s+de\s+)?)?retraite\s+(?:massive[sx]?|en\s+masse)\b"),
    re.compile(r"\bniveau\s+de\s+tension\s+\d{4}\b"),
    re.compile(r"\bfap\s+(?:[a-z]\d[a-z]?|\d+)\b", re.IGNORECASE),
    re.compile(r"\bdesequilibre[sx]?\s+(?:potentiel|recrutement)"),
]


# France Comp blocs RNCP — compétences certifiées par diplôme/titre.
# Détecte les questions sur le contenu pédagogique d'un diplôme : ce qu'on
# y apprend, les blocs validables, les savoir-faire certifiés. Couvre aussi
# les références explicites à RNCP (numéro de fiche) et VAE/validation
# partielle par bloc — usages opérationnels typiques des étudiants en
# reconversion ou phase (b)/(c) du scope élargi.
_PATTERNS_DOMAIN_COMPETENCES_CERTIF = [
    re.compile(r"\bbloc[sx]?\s+(?:de\s+)?competence[sx]?\b"),
    re.compile(r"\bcompetence[sx]?\s+(?:certifie[a-z]*|attestee[sx]?|valide[a-z]*)\b"),
    re.compile(r"\bcompetence[sx]?\s+(?:acquise[sx]?|developpee[sx]?)\s+(?:apres|en\s+sortant|grace\s+a)"),
    re.compile(r"\bque\s+(?:vais|va[a-z]*)?[\s-]?(?:je|on|tu)\s+apprendre\b"),
    re.compile(r"\bce\s+que\s+(?:je|on)\s+(?:vais|va)\s+apprendre\b"),
    re.compile(r"\bquel(?:s|les)?\s+(?:competences?|savoir[s\-]faire|skills?)\b"),
    re.compile(r"\bsavoir[\s\-]faire\s+(?:certifie[a-z]*|valide[a-z]*|acquis)\b"),
    re.compile(r"\b(?:objectif|programme)[sx]?\s+(?:pedagogique[sx]?|de\s+formation)\b"),
    re.compile(r"\bcontenu[sx]?\s+(?:du|de\s+(?:la|l['e]\s*))?(?:bts|but|licence|master|diplom|formation|certif)"),
    re.compile(r"\bque\s+(?:permet[a-z]*\s+(?:de\s+)?(?:faire|valider))\b"),
    re.compile(r"\brncp\s*\d+"),
    re.compile(r"\bvalidation\s+(?:partielle|par\s+bloc[sx]?)\b"),
    re.compile(r"\bvae\s+(?:par\s+bloc[sx]?|partielle)\b"),
]


_PATTERNS_DOMAIN_FORMATION_INSERTION = [
    re.compile(r"\binsertion\s+(?:apres|post)\s+(?:un\s+|une\s+|le\s+|la\s+)?(?:bac\s+pro|cap|bts)\b"),
    re.compile(r"\btaux\s+(?:d['e]\s*)?emploi\s+(?:apres|post)\s+(?:un\s+|une\s+|le\s+|la\s+)?(?:bac\s+pro|cap|bts|lycee\s+pro)\b"),
    re.compile(r"\b(?:insertion|emploi|debouches)\s+(?:bac\s+pro|cap|bts)\b"),
    re.compile(r"\b(?:que\s+devien)\w*\s+(?:les|des)\s+(?:diplomes?|sortants?)\s+(?:de\s+)?(?:bac\s+pro|cap)\b"),
    re.compile(r"\binserjeunes\b"),
    re.compile(r"\blycee\s+pro\s+(?:apres|insertion|debouches?)\b"),
    re.compile(r"\b(?:taux|chance)[a-z]*\s+(?:d['e]\s*)?(?:emploi|insertion)\s+(?:par|selon)\s+(?:specialit|formation)\b"),
    re.compile(r"\bcontinue[a-z]*\s+(?:ses\s+|mes\s+|leurs\s+)?etude[sx]?\s+apres\s+(?:un\s+|une\s+)?(?:bac\s+pro|cap)\b"),
    re.compile(r"\bpoursuite\s+(?:d['e]\s*)?etudes?\s+(?:apres|post)\s+(?:un\s+|une\s+)?(?:bac\s+pro|cap)\b"),
]

_PATTERNS_DOMAIN_FINANCEMENT_ETUDES = [
    re.compile(r"\b(?:bourse|aide|financement|subvention)[sx]?\s+(?:etudiant[a-z]*|formation|etudes?)\b"),
    re.compile(r"\b(?:comment|aide[sx]?)\s+(?:financer|payer)\s+(?:mes?|ses?)\s+(?:etudes?|formation)\b"),
    re.compile(r"\b(?:bourse[sx]?\s+crous|crous\s+bourse[sx]?)\b"),
    re.compile(r"\bbourse[sx]?\s+sur\s+critere[sx]?\s+sociaux?\b"),
    re.compile(r"\bcpf\b"),
    re.compile(r"\bcompte\s+personnel\s+(?:de\s+)?formation\b"),
    re.compile(r"\b(?:ptp|projet\s+de\s+transition\s+professionnelle|transitions?\s+pro)\b"),
    re.compile(r"\bafdas\b|\bopco\b|\bconstructys\b|\bakto\b"),
    re.compile(r"\bagefiph\b|\bfiphfp\b|\brqth\b"),
    re.compile(r"\b(?:cej|contrat\s+(?:d['e]\s*)?engagement\s+jeunes?)\b"),
    re.compile(r"\bgarantie\s+jeunes?\b"),
    re.compile(r"\b(?:apl|aide\s+au\s+logement)\s+(?:etudiant|crous|paje)\b"),
    re.compile(r"\bdispositif[sx]?\s+(?:de\s+)?financement\b"),
    re.compile(r"\bcombien\s+(?:coute|fait|prevoir)\s+(?:.*?)?(?:etude|formation|ecole)"),
    re.compile(r"\b(?:cout|cout\s+annuel|frais)[sx]?\s+(?:de\s+(?:la|l['e]\s*))?(?:formation|etudes?|ecole|inscription)\b"),
    re.compile(r"\b(?:reconversion|reorientat)[a-z]*\s+(?:financement|comment\s+financer|aide[sx]?)\b"),
    re.compile(r"\b(?:visale|caution|garantie\s+locative)\b"),
    # Note : VAE pattern restreint pour éviter conflit avec compétences_certif
    # (validation par blocs VAE = competences_certif). VAE comme financement
    # nécessite un contexte explicite "financement / coût / prise en charge".
    re.compile(r"\b(?:financement|prise\s+en\s+charge|aide|cout)\s+(?:vae|validation\s+des\s+acquis)\b"),
    re.compile(r"\b(?:vae|validation\s+des\s+acquis)\s+(?:.{0,40})?(?:financ|cout|prise\s+en\s+charge|payer|paie)"),
]

_PATTERNS_DOMAIN_TERRITOIRE_DROM = [
    re.compile(r"\b(?:drom|com|outre[\s\-]mer|outremer)\b"),
    re.compile(r"\b(?:guadeloupe|martinique|guyane|la\s+reunion|reunion|mayotte)\b"),
    re.compile(r"\b(?:departement|region)\s+(?:97[1-6]|d['e]\s*outre[\s\-]mer)\b"),
    re.compile(r"\b(?:antille[sx]?|caraibe[sx]?|ocean\s+indien)\b"),
    re.compile(r"\bladom\b"),
    re.compile(r"\b(?:passeport\s+mobilite|mobilite\s+(?:outre[\s\-]mer|metropole))\b"),
    re.compile(r"\b(?:sma|service\s+militaire\s+adapte)\b"),
    re.compile(r"\binsularite\b"),
]

_PATTERNS_DOMAIN_VOIE_PRE_BAC = [
    # Patterns "découverte / catalogue / liste" — distinguer voie_pre_bac (Sprint 6 axe 3a)
    # des cas de transition individuelle "je suis en CAP, je veux passer en bac pro"
    # qui restent formation-centric (None).
    re.compile(r"\b(?:specialite|filiere)[sx]?\s+(?:de\s+)?(?:bac\s+pro|cap|bp|mc)\b"),
    # Spot-check V5 2026-05-14 Phase 1.4 — Q11 régression : la formulation
    # naturelle "spécialités possibles en bac pro agriculture" n'était pas
    # capturée car le pattern ci-dessus exige "specialites (de) bac pro"
    # directement collés. Variant : autoriser 1 mot intermédiaire (possibles
    # / disponibles / offertes...) + préposition élargie (en/dans/du/d').
    re.compile(r"\b(?:specialite|filiere)[sx]?\s+\w+\s+(?:de\s+|en\s+|dans\s+|du\s+|d['e]?\s+)?(?:bac\s+pro|cap|bp|mc)\b"),
    re.compile(r"\b(?:liste|catalogue|toutes?\s+les?|quelle[sx]?)\s+(?:specialite[sx]?|formations?)\s+(?:bac\s+pro|cap|de\s+bac\s+pro)\b"),
    re.compile(r"\b(?:choisir|orientation)\s+(?:apres|post)\s+(?:la\s+)?(?:troisieme|3eme)\b"),
    re.compile(r"\bcatalogue\s+(?:bac\s+pro|cap)\b"),
    re.compile(r"\b(?:bac\s+pro|cap)\s+(?:metier[sx]?|specialit)"),
    re.compile(r"\bquels?\s+(?:bac\s+pro|cap)\b"),
    re.compile(r"\bbac\s+pro\s+(?:en|dans)\s+(?:cyber|industrie|electricite|agriculture|tourisme|hotellerie|commerce|sante|sport|art)"),
    re.compile(r"\bcap\s+(?:en|dans)\s+(?:cuisine|petite\s+enfance|coiffure|electricien|patissier|industrie|hotellerie|restauration)"),
    re.compile(r"\b(?:liste|catalogue|toutes?\s+les?)\s+(?:des\s+)?(?:bac\s+pro|cap)\s+(?:en|dans)\b"),
    re.compile(r"\b(?:liste|catalogue|toutes?)\s+(?:des\s+)?cap\b"),
    re.compile(r"\bmention\s+complementaire\s+(?:apres|en|comment|liste)"),
    re.compile(r"\b(?:contenu|programme)\s+(?:du|de\s+(?:la|l['e]\s*))?\s*(?:bac\s+pro|cap)\b"),
    re.compile(r"\bbaccalaureat\s+professionnel\s+(?:specialit|liste|catalogue|metier)"),
    # Note : `\bbac\s+pro\b` standalone retiré pour éviter de capturer les
    # cas de transition individuelle "je veux passer en bac pro" qui doivent
    # rester formation-centric. Le routing voie_pre_bac cible explicitement
    # les questions catalogue / découverte / programme.
]


def classify_domain_hint(question: str) -> str | None:
    """Retourne un hint de domain multi-corpus (ADR-049) ou None.

    Hint orthogonal au `INTENT_*` (les 2 cohabitent : un même question peut
    être COMPARAISON + DOMAIN_HINT_APEC). Le hint guide le reranker pour
    boost le bon corpus retrievable. None = formation-centric par défaut
    (comportement pre-ADR-049 préservé).

    Priorité de détection (du plus spécifique au plus générique) :
    1. APEC (marché du travail cadres) — termes très spécifiques
    2. Métier prospective DARES (métiers 2030 / postes à pourvoir 2030)
    3. Territoire DROM (Sprint 7 — Guadeloupe / Martinique / Guyane / Réunion / Mayotte)
    4. Financement études (Sprint 7 — bourses / CPF / aides)
    5. INSEE salaire (médian / cadre / employé / PCS)
    6. Insertion pro (taux insertion à N mois post bac+3+)
    7. Formation insertion (Sprint 7 — bac pro/CAP/BTS insertion via Inserjeunes)
    8. Voie pré-bac (Sprint 7 — BAC PRO + CAP catalogue spécialités)
    9. Compétences certifiées RNCP (blocs / contenu pédagogique)
    10. Parcours bacheliers (taux réussite licence × bac × mention)
    11. CROUS (logement étudiant / vie étudiante)
    12. Métier (profession / devenir / que fait un X)

    Sprint 7 Action 5 : ajout des 4 nouveaux hints (axes Sprint 6 :
    formation_insertion, financement_etudes, territoire_drom, voie_pre_bac)
    pour router les queries vers les nouveaux corpora curated/aggregés.
    """
    if not question or not question.strip():
        return None

    norm = _strip_accents(question.lower())

    # Vague 3.4 — Calendrier Parcoursup/MonMaster (priorité haute : signaux
    # très spécifiques "quand/date/phase/voeux" combinés à la plateforme)
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_CALENDRIER):
        return DOMAIN_HINT_CALENDRIER

    if any(p.search(norm) for p in _PATTERNS_DOMAIN_APEC):
        return DOMAIN_HINT_APEC
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_METIER_PROSPECTIVE):
        return DOMAIN_HINT_METIER_PROSPECTIVE
    # Sprint 7 axes 2 + 4 prioritaires (signaux très spécifiques DROM / financement)
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_TERRITOIRE_DROM):
        return DOMAIN_HINT_TERRITOIRE_DROM
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_FINANCEMENT_ETUDES):
        return DOMAIN_HINT_FINANCEMENT_ETUDES
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_INSEE_SALAIRE):
        return DOMAIN_HINT_INSEE_SALAIRE
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_INSERTION_PRO):
        return DOMAIN_HINT_INSERTION_PRO
    # Sprint 7 axe 3b — bac pro / CAP / BTS insertion (Inserjeunes)
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_FORMATION_INSERTION):
        return DOMAIN_HINT_FORMATION_INSERTION
    # Sprint 7 axe 3a — voie pré-bac catalogue qualitatif
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_VOIE_PRE_BAC):
        return DOMAIN_HINT_VOIE_PRE_BAC
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_COMPETENCES_CERTIF):
        return DOMAIN_HINT_COMPETENCES_CERTIF
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_PARCOURS):
        return DOMAIN_HINT_PARCOURS
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_CROUS):
        return DOMAIN_HINT_CROUS
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_METIER):
        return DOMAIN_HINT_METIER
    return None


def _has_geographic_marker(question_norm: str) -> bool:
    """Detect a French city or region by token match. Uses a closed
    set rather than NER for speed and determinism."""
    tokens = re.findall(r"[a-z][a-z\-]+", question_norm)
    if any(t in _FRENCH_CITIES for t in tokens):
        return True
    for region in _FRENCH_REGIONS:
        if region in question_norm:
            return True
    return False


def classify_intent(question: str) -> str:
    """Return one of the INTENT_* constants for the given question."""
    if not question or not question.strip():
        return INTENT_GENERAL

    norm = _strip_accents(question.lower())

    # Chantier 2 (2026-05-03) : factual_pointed PRIORITÉ HAUTE — questions
    # qui demandent UN chiffre/fait précis sur UNE formation. Si match,
    # le router pipeline tentera un SELECT structuré (lookup déterministe,
    # zero hallu). Doit dominer comparaison car « taux d'accès EFREI vs
    # ESEA » est techniquement une comparaison mais doit aussi déclencher
    # le SELECT (le router décidera si comparaison ou single-lookup selon
    # le nombre d'entités extraites).
    if any(p.search(norm) for p in _PATTERNS_FACTUAL_POINTED):
        return INTENT_FACTUAL_POINTED

    # Specific patterns first — order matters where intents could
    # overlap (e.g. a comparison between two cities should still be
    # classified as comparaison, not geographic).
    if any(p.search(norm) for p in _PATTERNS_COMPARAISON_NORM):
        return INTENT_COMPARAISON
    if any(p.search(question) for p in _PATTERNS_COMPARAISON_RAW):
        return INTENT_COMPARAISON

    # Realisme: grade mentions and selectivity language are unambiguous.
    if any(p.search(norm) for p in _PATTERNS_REALISME):
        return INTENT_REALISME

    if any(p.search(norm) for p in _PATTERNS_PASSERELLES):
        return INTENT_PASSERELLES

    if any(p.search(norm) for p in _PATTERNS_CONCEPTUAL):
        return INTENT_CONCEPTUAL

    if any(p.search(norm) for p in _PATTERNS_DECOUVERTE):
        return INTENT_DECOUVERTE

    # Geographic last because a city mention inside a comparison or
    # realisme question shouldn't override the more specific intent.
    if _has_geographic_marker(norm):
        return INTENT_GEOGRAPHIC

    return INTENT_GENERAL


def intent_to_config(intent: str) -> IntentConfig:
    """Map an intent class to its retrieval strategy. Unknown intents
    fall back to INTENT_GENERAL so callers never crash on typos."""
    return _CONFIGS.get(intent, _CONFIGS[INTENT_GENERAL])


# --- Tier 2.3 : format guidance injected into the user prompt ---

_FORMAT_GUIDANCE: dict[str, str] = {
    INTENT_COMPARAISON: (
        "Type de question détecté : comparaison. Utilise obligatoirement "
        "un tableau côte-à-côte pour contraster les options, pas un "
        "Plan A/B/C. Termine par une synthèse de 2-3 lignes qui oriente "
        "selon le profil."
    ),
    INTENT_CONCEPTUAL: (
        "Type de question détecté : conceptuelle / définitionnelle. "
        "Réponds de façon didactique et concise (100-200 mots). Pas de "
        "Plan A/B/C, pas de fiches comme exemples — explique le concept, "
        "son fonctionnement, et les cas typiques."
    ),
    INTENT_DECOUVERTE: (
        "Type de question détecté : découverte / exploration. Les fiches "
        "couvrent cyber / data / santé — si la question sort de ces "
        "domaines, sors du corpus et propose en (connaissance générale) "
        "des métiers interdisciplinaires ou au-delà du périmètre actuel. "
        "Ne restreins pas la réponse aux seules fiches disponibles."
    ),
    INTENT_REALISME: (
        "Type de question détecté : réalisme / faisabilité. Sois direct "
        "et cash sur la faisabilité du projet. Appuie-toi sur les taux, "
        "les chiffres, les profils admis. Si l'objectif n'est pas réaliste, "
        "dis-le d'abord, puis propose des alternatives chiffrées."
    ),
    INTENT_GEOGRAPHIC: (
        "Type de question détecté : géographique. Privilégie la proximité "
        "demandée, mais cite au moins 3 villes distinctes si la question "
        "laisse du jeu. Mentionne les distances ou temps de transport "
        "quand pertinent."
    ),
    INTENT_PASSERELLES: (
        "Type de question détecté : passerelles / réorientation. Décris "
        "les chemins intermédiaires étape par étape (Étape 1 → Étape 2 → "
        "Étape 3). Inclus admissions parallèles, VAE/VAP, validation "
        "d'acquis, calendriers clés."
    ),
    INTENT_GENERAL: (
        "Type de question détecté : générale. Structure en Plan A/B/C "
        "condensé (1-2 lignes par plan). Termine par une section "
        "« Attention aux pièges » (1-3 puces)."
    ),
    INTENT_FACTUAL_POINTED: (
        "Type de question détecté : factuelle pointue. Cette question "
        "vise UN chiffre / UN fait précis sur UNE formation nommée. "
        "Réponds DIRECTEMENT et brièvement (1-2 phrases) en citant la "
        "source exacte. Si l'info n'est pas dans <fiches_rag>, applique "
        "le fallback unifié « Je n'ai pas l'information sur [X] dans "
        "mes sources vérifiées » — NE FABRIQUE PAS un chiffre plausible."
    ),
}


def intent_to_format_guidance(intent: str) -> str:
    """Map an intent class to a format hint injected into the user
    prompt. The rules themselves are in SYSTEM_PROMPT — this classifier
    only tells the LLM which rule applies. Unknown intents fall back
    to INTENT_GENERAL."""
    return _FORMAT_GUIDANCE.get(intent, _FORMAT_GUIDANCE[INTENT_GENERAL])
