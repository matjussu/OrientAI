"""ProfileClarifier — Sprint 1 axe B agentique.

Extraction structurée d'un profil utilisateur depuis une query libre.
Mistral function-calling avec `tool_choice="any"` (force le call) sur
l'unique tool `extract_user_profile`.

Le profil retourné guide le routing retrieval (Sprints 2-4) :
- `age_group` + `education_level` filtrent les corpora pertinents
- `sector_interest` pondère le ranking par domaine d'intérêt
- `region` active les corpora régionaux (APEC / DARES)
- `intent_type` route vers les patterns reranker existants
- `urgent_concern` flag pour adoucir le ton

Cf ADR-051 pour le rationale architectural.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from typing import Optional

from mistralai.client import Mistral

from src.agent.cache import LRUCache
from src.agent.retry import call_with_retry
from src.agent.tool import Tool


# --- Profile dataclass (typed output) ---


VALID_AGE_GROUPS = {
    "lyceen_2nde",
    "lyceen_terminale",
    "bachelier_general",
    "bachelier_techno",
    "bachelier_pro",
    "etudiant_l1_l3",
    "etudiant_master",
    "adulte_25_45",
    "professionnel_actif",  # alias pratique : adulte avec emploi, pas
                            # de focus sur tranche d'âge précise
    "parent_lyceen",
    "professionnel_education",
    "other_or_unknown",
}

VALID_EDUCATION_LEVELS = {
    "infra_bac",  # 2nde, 1ère
    "terminale",
    "bac_obtenu",
    "bac+1",
    "bac+2",
    "bac+3",
    "bac+4",  # ajout post-audit Sprint 2 (PR #76 audit 48q) :
              # le LLM invente naturellement bac+4 pour M1. Pas dans
              # le système LMD officiel (bac+3 / bac+5 / bac+8) mais
              # utile pour tracer l'étape M1 incomplet.
    "bac+5",
    "bac+8_doctorat",
    "professionnel_actif",
    "unknown",
}

VALID_INTENT_TYPES = {
    "orientation_initiale",
    "reorientation_etude",
    "reconversion_pro",
    "comparaison_options",
    "decouverte_filieres",
    "info_metier_specifique",
    "demarche_administrative",
    "conceptuel_definition",
    "conseil_strategique",
    "other",
}


@dataclass
class Profile:
    """Profil utilisateur extrait par ProfileClarifier.

    Champs core (toujours présents) :
    - age_group : catégorie d'âge / situation
    - education_level : niveau d'études actuel
    - intent_type : nature de la demande

    Champs optionnels :
    - sector_interest : liste de secteurs / domaines mentionnés
    - region : région française mentionnée (libellé canonique)
    - urgent_concern : flag stress / urgence détecté
    - confidence : niveau de confiance auto-rapporté du LLM (0-1)
    - notes : annotations libres du LLM

    Champs étendus MODE RÉCIT (1b, ordre #137) — additifs et
    backward-compatibles (defaults sûrs). Peuplés uniquement par
    `clarify_narrative()` ; restent vides sur le chemin `clarify()`
    classique pour ne pas perturber la pipeline agentique / le banc 100q :
    - a_eviter : ce que l'utilisateur veut explicitement éviter
    - contraintes : alternance, durée, rémunération, distance, budget...
    - mobilite : disposition géographique (libellé libre) ou None
    - spans : best-effort, facette -> extrait verbatim du récit qui la justifie
    """

    age_group: str
    education_level: str
    intent_type: str
    sector_interest: list[str]
    region: Optional[str] = None
    urgent_concern: bool = False
    confidence: float = 0.5
    notes: Optional[str] = None
    # --- Champs étendus mode récit (1b) ---
    a_eviter: list[str] = field(default_factory=list)
    contraintes: list[str] = field(default_factory=list)
    mobilite: Optional[str] = None
    spans: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def is_valid(self) -> bool:
        """Sanity check des enums core + types des champs étendus (1b)."""
        return (
            self.age_group in VALID_AGE_GROUPS
            and self.education_level in VALID_EDUCATION_LEVELS
            and self.intent_type in VALID_INTENT_TYPES
            and isinstance(self.sector_interest, list)
            and 0.0 <= self.confidence <= 1.0
            and isinstance(self.a_eviter, list)
            and isinstance(self.contraintes, list)
            and isinstance(self.spans, dict)
            and (self.mobilite is None or isinstance(self.mobilite, str))
        )


# --- Tool definition (Mistral function-calling JSON schema) ---


PROFILE_TOOL_PARAMS_SCHEMA = {
    "type": "object",
    "properties": {
        "age_group": {
            "type": "string",
            "enum": sorted(VALID_AGE_GROUPS),
            "description": (
                "Catégorie d'âge / situation de l'utilisateur. "
                "Choisis 'other_or_unknown' si la query ne donne pas "
                "assez d'indices."
            ),
        },
        "education_level": {
            "type": "string",
            "enum": sorted(VALID_EDUCATION_LEVELS),
            "description": (
                "Niveau d'études actuel ou dernier obtenu. "
                "'professionnel_actif' pour un adulte en poste sans "
                "info académique récente. 'unknown' si non déterminable."
            ),
        },
        "intent_type": {
            "type": "string",
            "enum": sorted(VALID_INTENT_TYPES),
            "description": (
                "Nature de la demande (cf doc OrientIA intent classifier). "
                "Une seule catégorie même si plusieurs intent secondaires."
            ),
        },
        "sector_interest": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Liste des secteurs / domaines mentionnés "
                "(ex: ['informatique', 'numérique'] pour 'BUT info data')"
                ". Vide si aucun secteur explicite."
            ),
        },
        "region": {
            "type": ["string", "null"],
            "description": (
                "Région française mentionnée (libellé officiel : "
                "'Île-de-France', 'Bretagne', 'La Réunion', etc.). "
                "null si non mentionnée."
            ),
        },
        "urgent_concern": {
            "type": "boolean",
            "description": (
                "True si la query exprime stress, peur, urgence "
                "(ex: 'j'ai peur', 'je galère', 'je ne sais pas quoi "
                "faire'). False sinon."
            ),
        },
        "confidence": {
            "type": "number",
            "description": (
                "Confiance auto-rapportée 0-1 sur l'extraction. "
                "0.3 si query très vague, 0.9 si query très explicite."
            ),
        },
        "notes": {
            "type": ["string", "null"],
            "description": (
                "Annotations libres : ambiguïtés détectées, indices "
                "implicites, contexte utile pour le routing aval. "
                "Max 200 caractères. Null si aucune note."
            ),
        },
    },
    "required": [
        "age_group", "education_level", "intent_type",
        "sector_interest", "urgent_concern", "confidence",
    ],
}


def _profile_clarifier_tool_func(**kwargs) -> dict:
    """Implémentation du Tool : valide les params et retourne le profil.

    Le LLM appelle ce tool avec les paramètres extraits. La fonction
    sert de validation finale (enum check, types) avant retour à
    l'agent loop. Utilisable hors agentique pour test.
    """
    try:
        profile = Profile(
            age_group=kwargs.get("age_group", "other_or_unknown"),
            education_level=kwargs.get("education_level", "unknown"),
            intent_type=kwargs.get("intent_type", "other"),
            sector_interest=kwargs.get("sector_interest", []) or [],
            region=kwargs.get("region"),
            urgent_concern=bool(kwargs.get("urgent_concern", False)),
            confidence=float(kwargs.get("confidence", 0.5)),
            notes=kwargs.get("notes"),
        )
    except (TypeError, ValueError) as e:
        return {"error": "profile_construction_failed", "message": str(e)}
    if not profile.is_valid():
        return {
            "error": "profile_validation_failed",
            "raw_input": {k: kwargs.get(k) for k in PROFILE_TOOL_PARAMS_SCHEMA["required"]},
        }
    return {"profile": profile.to_dict(), "valid": True}


PROFILE_CLARIFIER_TOOL = Tool(
    name="extract_user_profile",
    description=(
        "Extrait un profil structuré (age_group, education_level, "
        "intent_type, sector_interest, region, urgent_concern, "
        "confidence) depuis la query libre de l'utilisateur. À "
        "appeler en première étape pour comprendre QUI parle et QUE "
        "veut comprendre, avant de chercher des formations ou métiers."
    ),
    parameters=PROFILE_TOOL_PARAMS_SCHEMA,
    func=_profile_clarifier_tool_func,
)


# --- Tool ÉTENDU mode récit (1b, ordre #137) ---
#
# Les vrais utilisateurs racontent un récit long (parcours + situation +
# envies + a-éviter). Le tool de base ne capture ni le `a_eviter`, ni les
# `contraintes`, ni la `mobilite` — pourtant essentiels pour qu'une bonne
# réponse "le montre" (cf definition_succes du seed). Ce tool ÉTEND le tool
# de base (mêmes enums core, réutilisés pour éviter tout drift) avec ces
# facettes + des `spans` best-effort (verbatim qui justifie chaque facette).


def _coerce_spans(raw) -> dict[str, str]:
    """Best-effort : normalise `spans` en dict[str, str], ignore le reste.

    Le LLM peut omettre des spans ou en renvoyer un type inattendu. On ne
    plante jamais et on ne vérifie pas que le span est un substring exact
    (paraphrase / accents tolérés) — best-effort assumé.
    """
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, str) and v.strip()}


NARRATIVE_EXTRA_PROPERTIES = {
    "a_eviter": {
        "type": "array",
        "items": {"type": "string"},
        "description": (
            "Ce que l'utilisateur veut EXPLICITEMENT éviter (ex: "
            "['commercial', 'vente'] ou ['études longues sans revenu']). "
            "Vide si rien d'exprimé. Crucial : une bonne réponse doit le "
            "prendre en compte visiblement."
        ),
    },
    "contraintes": {
        "type": "array",
        "items": {"type": "string"},
        "description": (
            "Contraintes pratiques exprimées : 'alternance', "
            "'rémunéré', 'études courtes', 'à distance', 'budget limité', "
            "etc. Vide si aucune."
        ),
    },
    "mobilite": {
        "type": ["string", "null"],
        "description": (
            "Disposition géographique exprimée, libellé libre : "
            "'mobile en France', 'rester à Lyon', 'pas mobile'. "
            "null si non exprimée."
        ),
    },
    "spans": {
        "type": "object",
        "additionalProperties": {"type": "string"},
        "description": (
            "Best-effort : pour chaque facette extraite, l'extrait VERBATIM "
            "du récit qui la justifie (ex: {'a_eviter': 'je ne veux surtout "
            "pas finir dans la vente'}). Sert la traçabilité. Omets une "
            "facette plutôt que d'inventer un extrait."
        ),
    },
}


NARRATIVE_PROFILE_TOOL_PARAMS_SCHEMA = {
    "type": "object",
    "properties": {
        **PROFILE_TOOL_PARAMS_SCHEMA["properties"],
        **NARRATIVE_EXTRA_PROPERTIES,
    },
    # Les champs étendus restent best-effort -> required = core de base.
    "required": PROFILE_TOOL_PARAMS_SCHEMA["required"],
}


def _narrative_profile_tool_func(**kwargs) -> dict:
    """Tool func étendu : valide + construit un Profile avec champs récit.

    Mêmes defaults sûrs que le tool de base sur le core, plus extraction
    best-effort de a_eviter / contraintes / mobilite / spans.
    """
    try:
        profile = Profile(
            age_group=kwargs.get("age_group", "other_or_unknown"),
            education_level=kwargs.get("education_level", "unknown"),
            intent_type=kwargs.get("intent_type", "other"),
            sector_interest=kwargs.get("sector_interest", []) or [],
            region=kwargs.get("region"),
            urgent_concern=bool(kwargs.get("urgent_concern", False)),
            confidence=float(kwargs.get("confidence", 0.5)),
            notes=kwargs.get("notes"),
            a_eviter=kwargs.get("a_eviter", []) or [],
            contraintes=kwargs.get("contraintes", []) or [],
            mobilite=kwargs.get("mobilite"),
            spans=_coerce_spans(kwargs.get("spans")),
        )
    except (TypeError, ValueError) as e:
        return {"error": "profile_construction_failed", "message": str(e)}
    if not profile.is_valid():
        return {
            "error": "profile_validation_failed",
            "raw_input": {k: kwargs.get(k) for k in NARRATIVE_PROFILE_TOOL_PARAMS_SCHEMA["required"]},
        }
    return {"profile": profile.to_dict(), "valid": True}


NARRATIVE_PROFILE_TOOL = Tool(
    name="extract_narrative_profile",
    description=(
        "Extrait un profil ÉTENDU depuis un RÉCIT long d'orientation : "
        "tout le profil de base PLUS ce que l'utilisateur veut éviter "
        "(a_eviter), ses contraintes pratiques, sa mobilité géographique, "
        "et des spans verbatim qui justifient chaque facette. À utiliser "
        "quand l'utilisateur raconte son parcours et sa situation en détail."
    ),
    parameters=NARRATIVE_PROFILE_TOOL_PARAMS_SCHEMA,
    func=_narrative_profile_tool_func,
)


# --- ProfileClarifier (interface haut niveau) ---


CLARIFIER_SYSTEM_PROMPT = (
    "Tu es ProfileClarifier d'OrientIA. Ta seule mission est d'extraire "
    "un profil structuré depuis la query libre de l'utilisateur en "
    "appelant l'outil `extract_user_profile`. Tu N'écris PAS de réponse "
    "narrative — tu invoques l'outil avec les paramètres extraits, "
    "c'est tout. Si la query est ambiguë, fais des best guesses et "
    "baisse `confidence` en conséquence."
)


NARRATIVE_CLARIFIER_SYSTEM_PROMPT = (
    "Tu es ProfileClarifier d'OrientIA en MODE RÉCIT. L'utilisateur "
    "raconte son parcours, sa situation, ses envies et ce qu'il veut "
    "éviter. Ta seule mission est d'extraire un profil structuré en "
    "appelant l'outil `extract_narrative_profile`. Tu N'écris PAS de "
    "réponse — tu invoques l'outil, c'est tout.\n"
    "Sois exhaustif sur les facettes RÉELLEMENT exprimées : en plus du "
    "profil de base, capture `a_eviter` (ce qui est explicitement rejeté), "
    "les `contraintes` pratiques (alternance, rémunération, durée, "
    "distance...) et la `mobilite` géographique. Pour chaque facette "
    "extraite, renseigne dans `spans` l'extrait VERBATIM du récit qui la "
    "justifie. N'invente RIEN : si une facette n'est pas exprimée, laisse-la "
    "vide plutôt que de deviner. Baisse `confidence` si le récit est vague."
)


@dataclass
class ProfileClarifier:
    """Wrapper haut niveau pour invoquer ProfileClarifier sur une query.

    Pattern :
        clarifier = ProfileClarifier(client)
        profile = clarifier.clarify("Je suis lycéen à La Réunion ...")
        # → Profile(age_group='lyceen_terminale', region='La Réunion', ...)

    En interne :
    - Force `tool_choice` sur `extract_user_profile` (single-call mode)
    - Parse les arguments retournés
    - Construit + valide la dataclass `Profile`
    - Retourne `Profile` ou raise `ValueError` si invalid
    - Retry exponential backoff sur 429 / 5xx (cf src/agent/retry.py)
    """

    client: Mistral
    model: str = "mistral-large-latest"
    # Mode récit (1b) : modèle small + temp 0 -> extraction déterministe et
    # économe (~0 crédit Claude), reproductible pour la boucle de jugement.
    narrative_model: str = "mistral-small-latest"
    timeout_ms: int = 60_000
    max_retries: int = 3
    initial_backoff: float = 2.0
    cache: LRUCache | None = None  # Sprint 3 (2b) — opt-in caching

    def clarify(self, query: str) -> Profile:
        """Extrait le profil depuis `query`. Raise ValueError si parse fail.

        Si `self.cache` est fourni, lookup d'abord (key = query). Cache
        hit → retour immédiat (~0ms, $0). Cache miss → Mistral call +
        store dans le cache.
        """
        # Sprint 3 (2b) — Cache lookup
        if self.cache is not None:
            cached = self.cache.get(query)
            if cached is not None:
                return cached

        messages = [
            {"role": "system", "content": CLARIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        response = call_with_retry(
            lambda: self.client.chat.complete(
                model=self.model,
                messages=messages,
                tools=[PROFILE_CLARIFIER_TOOL.to_mistral_schema()],
                tool_choice="any",  # force le call
            ),
            max_retries=self.max_retries,
            initial_backoff=self.initial_backoff,
        )
        msg = response.choices[0].message
        if not msg.tool_calls:
            raise ValueError(
                f"ProfileClarifier: Mistral n'a pas appelé le tool "
                f"(content='{(msg.content or '')[:200]}')"
            )
        tc = msg.tool_calls[0]
        if tc.function.name != PROFILE_CLARIFIER_TOOL.name:
            raise ValueError(
                f"ProfileClarifier: tool inattendu '{tc.function.name}'"
            )
        try:
            args = json.loads(tc.function.arguments)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"ProfileClarifier: JSON parse failed "
                f"(args={tc.function.arguments[:200]!r}, err={e})"
            )
        result = PROFILE_CLARIFIER_TOOL.call(**args)
        if "error" in result:
            raise ValueError(
                f"ProfileClarifier: tool returned error: {result}"
            )
        profile = Profile(**result["profile"])
        # Sprint 3 (2b) — Cache store post-success
        if self.cache is not None:
            self.cache.set(query, profile)
        return profile

    # --- Mode récit (1b, ordre #137) ---

    _NARRATIVE_CACHE_PREFIX = "narrative::"

    def clarify_narrative(self, query: str) -> Profile:
        """Extraction ÉTENDUE pour le mode récit. NE RAISE JAMAIS.

        Diffère de `clarify()` :
        - modèle `narrative_model` (small) + temperature=0 (déterministe)
        - tool étendu `extract_narrative_profile` (a_eviter / contraintes /
          mobilite / spans best-effort)
        - FALLBACK SILENCIEUX : toute défaillance (pas de tool_call, tool
          inattendu, JSON invalide, tool error, exception réseau après
          retries) retourne un Profile de repli sûr (`confidence=0.0`,
          `notes='narrative_fallback:<raison>'`) au lieu de lever. Le mode
          récit doit dégrader proprement, jamais casser le pipeline aval.
          Le catch large est INTENTIONNEL (exigence d'ordre) ; la raison est
          tracée dans `notes` pour l'observabilité — donc pas de catch muet.
        """
        if self.cache is not None:
            cached = self.cache.get(self._NARRATIVE_CACHE_PREFIX + query)
            if cached is not None:
                return cached

        try:
            messages = [
                {"role": "system", "content": NARRATIVE_CLARIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ]
            response = call_with_retry(
                lambda: self.client.chat.complete(
                    model=self.narrative_model,
                    messages=messages,
                    tools=[NARRATIVE_PROFILE_TOOL.to_mistral_schema()],
                    tool_choice="any",  # force le call
                    temperature=0.0,    # déterministe
                ),
                max_retries=self.max_retries,
                initial_backoff=self.initial_backoff,
            )
            msg = response.choices[0].message
            if not msg.tool_calls:
                return self._narrative_fallback("no_tool_call")
            tc = msg.tool_calls[0]
            if tc.function.name != NARRATIVE_PROFILE_TOOL.name:
                return self._narrative_fallback(f"unexpected_tool:{tc.function.name}")
            args = json.loads(tc.function.arguments)
            result = NARRATIVE_PROFILE_TOOL.call(**args)
            if "error" in result:
                return self._narrative_fallback(f"tool_error:{result.get('error')}")
            profile = Profile(**result["profile"])
        except Exception as e:  # noqa: BLE001 — fallback silencieux voulu (cf docstring)
            return self._narrative_fallback(f"exception:{type(e).__name__}")

        if self.cache is not None:
            self.cache.set(self._NARRATIVE_CACHE_PREFIX + query, profile)
        return profile

    def _narrative_fallback(self, reason: str) -> Profile:
        """Profil de repli sûr pour le mode récit (confidence=0.0).

        Signale au pipeline aval (1c retrieval) qu'aucune extraction fiable
        n'a eu lieu -> il doit retomber sur la query brute plutôt que de se
        fier au profil. La raison est conservée dans `notes`.
        """
        return Profile(
            age_group="other_or_unknown",
            education_level="unknown",
            intent_type="other",
            sector_interest=[],
            region=None,
            urgent_concern=False,
            confidence=0.0,
            notes=f"narrative_fallback:{reason}",
        )
