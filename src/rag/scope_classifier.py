"""ScopeClassifier — gating amont du pipeline OrientIA.

Décide AVANT le retrieval/generation si une question doit être traitée par
le pipeline RAG (`in_scope`) ou court-circuitée par une réponse pré-écrite
(`out_of_scope` ou `urgent`).

3 catégories :

- **in_scope** : toute question d'orientation académique ou professionnelle
  post-bac (formations, métiers, parcours, choix, réorientation, financement,
  insertion, comparaison écoles, etc.). Inclut les domaines mal couverts par
  le corpus actuel (santé, droit, archi, vétérinaire) — c'est le pipeline RAG
  qui décidera honnêtement de répondre ou de fallback.

- **out_of_scope** : question NON liée à l'orientation (devoirs scolaires,
  cuisine, blagues, météo, sport en tant que loisir, code/dev hors orientation,
  questions personnelles non liées). Réponse pré-écrite qui réoriente vers
  l'orientation post-bac.

- **urgent** : signal de mal-être grave, idéations suicidaires, violences
  subies, harcèlement intense, détresse psychologique aiguë. Réponse imposée
  qui (a) reconnaît la souffrance, (b) redirige vers les numéros d'urgence
  appropriés (3114 prévention suicide, 3919 violences femmes, 119 enfance
  maltraitance, 30 18 SOS Amitié). NE TENTE PAS de "répondre" — ce n'est pas
  notre rôle.

Stratégie :
1. Pré-filter regex pour les signaux clairs urgent (mots-clés forts) — gain
   latence + sécurité (pas de risque LLM rate l'urgence)
2. LLM Mistral Small `mistral-small-latest` pour les autres (out_of_scope vs
   in_scope) — déterministe-difficile à faire en regex (formulations indirectes
   "j'en peux plus de l'école", "à quoi bon faire des études")
3. Default conservateur : si LLM échoue ou ambigu, traiter comme `in_scope`
   (mieux pipeline qui dit honnêtement qu'il sait pas que refus accidentel)

Coût : ~$0.0005/q + 0.5-1s latency. Acceptable.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

ScopeLabel = Literal["in_scope", "out_of_scope", "urgent", "identity", "greeting"]


# ─────────────── Regex pré-filter URGENCE (signaux forts uniquement) ───────────────

# Patterns explicites d'urgence vie/mal-être grave. Conservatifs : ne couvrent
# que les signaux non-ambigus. Le LLM rattrape les formulations indirectes.
_URGENT_PATTERNS = [
    # Suicide / fin de vie
    re.compile(r"\bsuicid[a-z]*\b", re.IGNORECASE),
    re.compile(r"\bme tuer\b", re.IGNORECASE),
    re.compile(r"\bme suicider\b", re.IGNORECASE),
    re.compile(r"\b(en finir|finir avec) (?:la vie|tout)\b", re.IGNORECASE),
    re.compile(r"\bplus envie de vivre\b", re.IGNORECASE),
    re.compile(r"\bne plus exister\b", re.IGNORECASE),
    re.compile(r"\b(disparait|disparaitre|disparaître)\b.*\bpour de bon\b", re.IGNORECASE),
    # Violences subies
    re.compile(r"\b(je suis|j'ai été) (battu|frappé|violent|abus)", re.IGNORECASE),
    re.compile(r"\b(violences? conjugales?|violences? domestiques?)\b", re.IGNORECASE),
    re.compile(r"\b(viol|agression sexuelle)\b", re.IGNORECASE),
    re.compile(r"\b(harcèlement|harcelement) (sexuel|scolaire) (subi|grave)\b", re.IGNORECASE),
    # Détresse psy aiguë
    re.compile(r"\b(crise (de )?(panique|angoisse) (intense|grave))\b", re.IGNORECASE),
    re.compile(r"\bje (vais|veux) m['e]\s*(faire du mal|automutil)", re.IGNORECASE),
]


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


def detect_urgent_signals_regex(question: str) -> list[str]:
    """Retourne la liste des patterns matchés (vide si aucun)."""
    matched = []
    for pattern in _URGENT_PATTERNS:
        if pattern.search(question):
            matched.append(pattern.pattern)
    return matched


# ─────────────── Regex pré-filter IDENTITÉ (qui es-tu / es-tu une IA) ───────────────

# Questions méta sur l'identité du système. Court-circuit gratuit (pas d'appel
# LLM) avec une réponse stable. Evite que ces questions classiques retombent
# dans `out_of_scope` (UX dégradée : "Cette question sort du cadre…") ou
# pire, déclenchent un retrieval RAG inutile.
_IDENTITY_PATTERNS = [
    re.compile(r"\b(?:tu\s+es|t['’]es)\s+qui\b", re.IGNORECASE),
    # `qui es-tu` / `qui es tu` / `qui estu` / `qui est tu` (typo "est" courante)
    re.compile(r"\bqui\s+(?:es|est)[-\s]?tu\b", re.IGNORECASE),
    re.compile(r"\b(?:tu\s+es|t['’]es)\s+quoi\b", re.IGNORECASE),
    re.compile(r"\bqu['’]es[-\s]tu\b", re.IGNORECASE),
    re.compile(r"\bqu['’]est[-\s]ce\s+que\s+tu\s+es\b", re.IGNORECASE),
    re.compile(r"\bes[-\s]tu\s+(?:une?\s+)?(?:IA|I\.A\.|intelligence\s+artificielle|robot|bot|chatbot|humain|une\s+personne)\b", re.IGNORECASE),
    re.compile(r"\b(?:tu\s+es|t['’]es)\s+(?:une?\s+)?(?:IA|I\.A\.|intelligence\s+artificielle|robot|bot|chatbot|humain|une\s+personne)\b", re.IGNORECASE),
    re.compile(r"\bpr[ée]sente[-\s]toi\b", re.IGNORECASE),
    re.compile(r"\bcomment\s+(?:tu\s+t['’]appelles|t['’]appelles[-\s]tu)\b", re.IGNORECASE),
    re.compile(r"\b(?:c['’]est\s+quoi|quel\s+est)\s+ton\s+nom\b", re.IGNORECASE),
    re.compile(r"\btu\s+(?:es|t['’]appelles)\s+orient", re.IGNORECASE),
]


# ─────────────── Regex pré-filter SALUTATION (bonjour, salut, hey…) ───────────────

# Salutations isolées sans question d'orientation derrière. Court-circuit avec
# une réponse chaleureuse qui invite à poser une question d'orientation.
# Évite que "Bonjour !" tombe en out_of_scope avec un message sec/froid.
#
# Les patterns matchent une question ENTIÈREMENT composée d'une salutation
# (avec éventuellement ponctuation et "ça va ?", "comment vas-tu ?"). Si
# la salutation est suivie d'une vraie question (ex : "Salut, je suis en
# terminale…"), on n'aura PAS de match strict et le pipeline traitera la
# vraie question normalement.
_GREETING_PATTERNS = [
    # Greeting word + optional ponctuation + optional small talk
    # ^(salut|hey|hello|bonjour|...)\W*(\W*ça va|comment vas-tu)?\W*$
    re.compile(
        r"^[\s\W]*(?:salut|hey|hello|bonjour|bonsoir|coucou|yo|hi|hola|"
        r"slt|cc|bjr|bsr)"
        r"(?:[\s,!.?]+(?:ça\s+va|comment\s+vas[-\s]?tu|comment\s+ça\s+va|tout\s+va\s+bien))?"
        r"[\s\W]*$",
        re.IGNORECASE,
    ),
]


def detect_greeting_signals_regex(question: str) -> list[str]:
    """Retourne la liste des patterns salutation matchés (vide si aucun)."""
    matched = []
    for pattern in _GREETING_PATTERNS:
        if pattern.search(question):
            matched.append(pattern.pattern)
    return matched


def detect_identity_signals_regex(question: str) -> list[str]:
    """Retourne la liste des patterns identité matchés (vide si aucun)."""
    matched = []
    for pattern in _IDENTITY_PATTERNS:
        if pattern.search(question):
            matched.append(pattern.pattern)
    return matched


# ─────────────── Réponses pré-écrites ───────────────

OUT_OF_SCOPE_RESPONSE = (
    "Cette question sort du cadre d'OrientAI, qui est spécialisé dans "
    "l'**orientation académique et professionnelle post-bac** (formations, "
    "métiers, parcours, choix d'écoles, réorientation, financement des "
    "études, insertion pro).\n\n"
    "As-tu une question d'orientation à me poser ? Quelques exemples :\n"
    "- *« Je suis en terminale, j'hésite entre prépa et BUT info »*\n"
    "- *« Comment se réorienter après une L2 de droit ? »*\n"
    "- *« Quelles écoles d'ingénieur en cybersécurité existent en Bretagne ? »*\n\n"
    "Pour toute autre question, je te suggère de t'adresser à la ressource "
    "appropriée (enseignant, ami, autre outil)."
)


IDENTITY_RESPONSE = (
    "Je suis **OrientAI** — une intelligence artificielle dédiée à "
    "l'**orientation académique et professionnelle française post-bac**.\n\n"
    "Je m'appuie **uniquement sur des données publiques officielles** : "
    "Parcoursup, ONISEP, le référentiel ROME des métiers, et les statistiques "
    "d'insertion InsertSup. Pas de données privées, pas de classements "
    "marketing — chaque chiffre que je cite est traçable à sa source.\n\n"
    "Je peux t'aider à explorer des formations, comparer des écoles, "
    "comprendre des métiers et leurs débouchés, identifier des passerelles "
    "ou des financements.\n\n"
    "Quelle est ta question d'orientation ?"
)


GREETING_RESPONSE = (
    "Salut ! 👋 Je suis **OrientAI**, ton assistant d'orientation académique "
    "et professionnelle post-bac.\n\n"
    "Je peux t'aider à explorer des **formations** (licence, BUT, BTS, "
    "écoles d'ingé/co, masters), comparer des **métiers**, comprendre des "
    "**parcours** ou trouver des **financements** d'études.\n\n"
    "Quelle est ta question d'orientation ?\n\n"
    "Quelques exemples si tu veux t'inspirer :\n"
    "- *« Je suis en terminale, j'hésite entre prépa et BUT info »*\n"
    "- *« Quelles écoles de cybersécurité en Bretagne ? »*\n"
    "- *« Comment se réorienter après une L2 de droit ? »*"
)


URGENT_RESPONSE = (
    "Je perçois dans ton message une **détresse importante**. Avant tout, "
    "ta sécurité et ton bien-être passent avant les questions d'orientation.\n\n"
    "**Numéros d'écoute gratuits, anonymes, 24h/24** :\n\n"
    "- **3114** — Numéro national de **prévention du suicide** "
    "(gratuit, confidentiel, professionnels formés)\n"
    "- **3919** — Violences faites aux femmes (gratuit, anonyme)\n"
    "- **119** — Enfance en danger / maltraitance (24h/24)\n"
    "- **30 18** — SOS Amitié, écoute généraliste (anxiété, isolement)\n"
    "- **15** — SAMU si urgence vitale immédiate\n\n"
    "Tu peux aussi en parler à une personne de confiance autour de toi : "
    "Psy-EN du lycée, infirmier·ère scolaire, médecin traitant, parent, ami·e.\n\n"
    "Je suis un outil d'orientation, pas un professionnel de santé mentale. "
    "Mais ces personnes et numéros sauront t'écouter et t'aider."
)


# ─────────────── LLM classifier (out_of_scope vs in_scope) ───────────────

_CLASSIFIER_SYSTEM_PROMPT = """Tu es un classifieur de scope pour OrientIA, un système d'orientation \
académique et professionnelle française post-bac.

## TA TÂCHE

Catégorise la question en EXACTEMENT UNE de ces 3 catégories : `in_scope`, \
`out_of_scope`, `urgent`. Tu réponds UNIQUEMENT en JSON.

## RÈGLE PRIORITAIRE (calibrée — détresse VITALE, pas stress d'orientation)

Si tu détectes un signal de **détresse psychologique GRAVE** menaçant la \
sécurité ou la santé de la personne (idéations suicidaires, envie d'en finir, \
violences subies, désespoir profond et GLOBAL sur la vie, auto-dévalorisation \
sévère hors contexte scolaire), classe **urgent**. La détresse vitale prime \
sur tout autre indice.

**Distinction cruciale** : le STRESS, l'ANGOISSE ou l'INDÉCISION liés au CHOIX \
d'orientation ne sont PAS de la détresse vitale — c'est le coeur de métier de \
l'outil. Un élève stressé par son orientation a besoin d'AIDE À L'ORIENTATION \
(in_scope), pas du 3114. Ne classe `urgent` que si la souffrance dépasse \
clairement le cadre scolaire/orientation et touche la sécurité de la personne. \
En cas de doute entre "stress d'orientation" et "détresse vitale", regarde si \
la personne demande de l'aide pour CHOISIR (-> in_scope) ou exprime un mal-être \
qui dépasse les études (-> urgent).

## NE PAS classer `urgent` (stress / indécision NORMALE d'orientation)

Ces formulations sont `in_scope` (ou `out_of_scope` si médical), JAMAIS urgent :
- "je sais pas quoi faire après le bac, aide-moi" -> in_scope (indécision normale)
- "je suis stressé·e / ça m'angoisse de pas savoir quoi choisir" -> in_scope
- "j'ai peur de me tromper de voie / de faire le mauvais choix" -> in_scope
- "je panique pour Parcoursup / mes voeux" -> in_scope
- "comment gérer mon anxiété/stress avant le bac" -> out_of_scope (médical), PAS urgent
Le stress face à une décision d'orientation est attendu et légitime : il appelle \
de l'accompagnement à l'orientation, pas une réponse de crise.

## CONTEXTE CONVERSATIONNEL

Si des messages précédents (`role: "user"` ou `"assistant"`) te sont fournis \
AVANT la question courante, ils représentent l'historique d'une conversation \
en cours. Tu dois en tenir compte pour juger si la question courante est in_scope.

**Règle clé** : un follow-up court qui dépend du contexte précédent (ex: \
"et à Lyon ?", "développe ce point", "celle-ci ?", "explique") est **in_scope** \
si le tour précédent était in_scope (orientation post-bac, formations, métiers, \
CROUS, financement, etc.). N'évalue PAS le follow-up isolément — c'est la \
combinaison contexte + question qui compte.

**Exemples** :
- Tour 1 user : "Y a-t-il des logements CROUS à Paris ?"
- Tour 1 assistant : "Oui, voici les résidences disponibles…"
- Tour 2 user : "et à Lyon ?" → **in_scope** (suite logique de la question CROUS)

- Tour 1 user : "Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité"
- Tour 2 user : "et l'INSA Lyon ?" → **in_scope** (suite comparaison écoles)

- Tour 1 user : "Quel est le métier de data scientist ?"
- Tour 2 user : "raconte-moi une blague" → **out_of_scope** (changement de sujet net)

## DÉFINITIONS

### `urgent` — Détresse psychologique (PRIORITÉ ABSOLUE)
Tout signal de mal-être grave : idéations suicidaires, violences subies, \
harcèlement intense, détresse psychologique aiguë.

**Formulations explicites** : "suicide", "me tuer", "en finir", "violences \
conjugales", "agressé·e", "battu·e".

**Formulations indirectes (TRÈS IMPORTANTES)** : "j'en peux plus", "à quoi bon", \
"personne ne m'aime", "tout va mal", "je suis nul·le", "je veux disparaître", \
"je n'ai plus de raison", "je suis seul·e et triste", "ma vie ne vaut rien", \
"plus de force", "je craque", "j'ai envie d'arrêter", "rien ne va".

### `out_of_scope` — Hors orientation post-bac/pro
Question SANS lien avec choix de formation, choix de métier, parcours étudiant.

**Exemples concrets** :
- Cuisine, recettes : "donne-moi une recette de gâteau"
- Météo, lieu, voyage : "quel temps à Paris ?", "où aller en vacances ?"
- Blagues, divertissement : "raconte-moi une blague", "fais-moi rire"
- Devoirs : "résous cet exercice de maths", "corrige ma dissertation"
- Politique, actualité : "que penses-tu de la réforme X ?"
- Vie privée non-orientation : "comment séduire ?", "conseils relation amoureuse"
- Programmation hors orientation : "écris-moi du code Python pour X"
- Salutations sans question : "bonjour", "ça va ?"
- Questions techniques généralistes : "comment marche internet ?"

### `in_scope` — Orientation post-bac/pro (TRÈS LARGE)
Toute question d'orientation académique ou professionnelle. **Même** si le \
domaine est mal couvert dans nos données (droit, santé, vétérinaire, archi, \
hôtellerie, art, sport, agriculture, etc.) → reste in_scope. Inclut :
- Formations : BTS, BUT, licence, master, écoles d'ingé/co/art/santé, prépa, \
doctorat, alternance, formation continue, certificats, MS
- Métiers : "devenir X", "que fait Y", "salaire de Z", débouchés, reconversion
- Parcours : passerelles, réorientation, après bac/L2/master, validation acquis
- Financement : bourses, CPF, prêt étudiant, frais
- Insertion pro : taux d'emploi, durée recherche, secteurs porteurs
- Comparaisons d'écoles, sélectivité, admission

## EXEMPLES (FEW-SHOT)

Question : "Quelles écoles d'ingé en cybersécurité en Bretagne ?"
→ {"label": "in_scope", "reason": "question orientation formations supérieures"}

Question : "Donne-moi une recette de gâteau au chocolat"
→ {"label": "out_of_scope", "reason": "demande culinaire sans lien orientation"}

Question : "Raconte-moi une blague drôle"
→ {"label": "out_of_scope", "reason": "demande de divertissement"}

Question : "Quelle est la météo à Paris cet après-midi ?"
→ {"label": "out_of_scope", "reason": "question météo, hors orientation"}

Question : "Je veux devenir avocat fiscaliste, quelles études ?"
→ {"label": "in_scope", "reason": "orientation vers métier juridique"}

Question : "Je n'ai plus envie de vivre, je pense au suicide"
→ {"label": "urgent", "reason": "idéation suicidaire explicite"}

Question : "À quoi bon continuer, j'en peux plus de tout, personne ne m'aime"
→ {"label": "urgent", "reason": "signal détresse multiple : à quoi bon + j'en peux plus + isolement"}

Question : "Je suis nul·le en cours, je sers à rien"
→ {"label": "urgent", "reason": "auto-dévalorisation grave, possible détresse"}

Question : "Je suis nul en maths, est-ce que je peux quand même faire ingénieur ?"
→ {"label": "in_scope", "reason": "auto-évaluation contextualisée à projet orientation"}

Question : "je sais pas quoi faire après le bac aide moi"
→ {"label": "in_scope", "reason": "indécision d'orientation normale, pas de détresse vitale"}

Question : "je suis hyper stressé et ça m'angoisse de pas savoir quoi choisir comme orientation, aide moi"
→ {"label": "in_scope", "reason": "stress lié au choix d'orientation = coeur de métier, pas urgent"}

Question : "Quel médicament pour calmer mon anxiété avant le bac ?"
→ {"label": "out_of_scope", "reason": "demande médicale hors orientation, mais PAS détresse vitale"}

Question : "Bonjour, ça va ?"
→ {"label": "out_of_scope", "reason": "salutation sans question d'orientation"}

## FORMAT RÉPONSE STRICT

Tu réponds UNIQUEMENT par ce JSON, sans markdown, sans texte autour :

{"label": "in_scope" | "out_of_scope" | "urgent", "reason": "<phrase courte>"}
"""


@dataclass(frozen=True)
class ScopeResult:
    label: ScopeLabel
    reason: str
    via: Literal["regex_urgent", "regex_identity", "regex_greeting", "llm", "fallback_in_scope"]
    pre_written_response: str | None = None  # texte à retourner si != in_scope


def _extract_json(raw: str) -> dict | None:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*?\}", raw)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


class ScopeClassifier:
    """Gate amont du pipeline OrientIA.

    Usage :
        clf = ScopeClassifier(client=mistral_client)
        result = clf.classify(question)
        if result.label != "in_scope":
            return result.pre_written_response  # court-circuit
        # sinon → continue le pipeline RAG normal

    Args:
        client: Mistral client (pour LLM cheap classification). Si None, fallback
            uniquement sur regex urgent + default in_scope (mode dégradé).
        model: par défaut mistral-small-latest (~$0.0005/q).
        timeout_ms: 5s default.
    """

    def __init__(
        self,
        client=None,
        model: str = "mistral-small-latest",
        timeout_ms: int = 5000,
    ):
        self.client = client
        self.model = model
        self.timeout_ms = timeout_ms

    def classify(
        self,
        question: str,
        history: list[dict] | None = None,
    ) -> ScopeResult:
        """Classifie une question en {in_scope, out_of_scope, urgent, identity, greeting}.

        Args:
            question: requête utilisateur courante.
            history: historique conversationnel optionnel (`[{role, content}]`).
                Quand fourni, le LLM classifier voit le contexte des messages
                précédents pour mieux juger les follow-ups type "et à Lyon ?",
                "développe ce point", qui isolément paraissent out_of_scope
                mais qui sont des suites légitimes d'une conversation
                in_scope. Default `None` = comportement stateless v1.
        """
        if not question or not question.strip():
            return ScopeResult(
                label="out_of_scope",
                reason="empty question",
                via="fallback_in_scope",
                pre_written_response=OUT_OF_SCOPE_RESPONSE,
            )

        # Étape 0bis : pré-filter regex IDENTITÉ ("qui es-tu", "es-tu une IA"…)
        # Court-circuit gratuit avec réponse stable. Placé avant urgent car
        # signal très spécifique et non-ambigu (un "qui es-tu" ne peut pas
        # être de la détresse).
        identity_matches = detect_identity_signals_regex(question)
        if identity_matches:
            return ScopeResult(
                label="identity",
                reason=f"regex identity matched: {identity_matches[0]}",
                via="regex_identity",
                pre_written_response=IDENTITY_RESPONSE,
            )

        # Étape 0ter : pré-filter regex SALUTATION ("bonjour", "salut !", "hey")
        # Court-circuit avec réponse chaleureuse + bridge vers orientation.
        # Évite le message "Cette question sort du cadre…" sec et froid.
        # Placé avant urgent : un "bonjour" seul n'est pas un signal détresse.
        greeting_matches = detect_greeting_signals_regex(question)
        if greeting_matches:
            return ScopeResult(
                label="greeting",
                reason=f"regex greeting matched: {greeting_matches[0][:60]}",
                via="regex_greeting",
                pre_written_response=GREETING_RESPONSE,
            )

        # Étape 1 : pré-filter regex URGENT (signaux forts non-ambigus)
        urgent_matches = detect_urgent_signals_regex(question)
        if urgent_matches:
            return ScopeResult(
                label="urgent",
                reason=f"regex urgent matched: {urgent_matches[0]}",
                via="regex_urgent",
                pre_written_response=URGENT_RESPONSE,
            )

        # Étape 2 : LLM classifier (out_of_scope vs in_scope vs urgent indirect)
        if self.client is None:
            # Mode dégradé : sans LLM, default in_scope (laisse le pipeline gérer)
            return ScopeResult(
                label="in_scope",
                reason="no LLM client provided, default in_scope",
                via="fallback_in_scope",
                pre_written_response=None,
            )

        try:
            # Bug fix Étape 2 (2026-05-06) : timeout dédié court (5s).
            # Le client Mistral global a un timeout 120s. Sans override ici,
            # un ReadTimeout sur Mistral Small fait stagner le ScopeClassifier
            # 120s et fallback in_scope → pipeline complet déclenché à tort
            # sur une question hors scope (S1 cuisine 128s, S3 blague 127s,
            # U2 distress indirect 129s observés en Étape 2 bench).
            # Cap à 5s : si l'API met plus, on dégrade en in_scope (le pipeline
            # gère honnêtement). Mistral Small répond normalement <2s.
            # Construction messages array : system → history (si fourni) → question.
            # Le LLM voit le contexte de la conversation précédente pour juger
            # correctement les follow-ups ("et à Lyon ?" après une question
            # CROUS Paris est in_scope, pas out_of_scope).
            classifier_messages: list[dict] = [
                {"role": "system", "content": _CLASSIFIER_SYSTEM_PROMPT}
            ]
            if history:
                # Cap à 4 derniers messages pour borner les tokens (le scope
                # classifier n'a pas besoin de toute la conversation pour
                # détecter le contexte général). Filtre les messages mal formés.
                for msg in history[-4:]:
                    role = msg.get("role")
                    content = msg.get("content")
                    if role in ("user", "assistant") and isinstance(content, str) and content:
                        classifier_messages.append({"role": role, "content": content})
            classifier_messages.append({"role": "user", "content": question})

            resp = self.client.chat.complete(
                model=self.model,
                max_tokens=200,
                messages=classifier_messages,
                response_format={"type": "json_object"},
                timeout_ms=self.timeout_ms,
                temperature=0.0,  # A1 déterminisme : même question -> même verdict
            )
            text = resp.choices[0].message.content or ""
        except Exception as e:
            # Mode dégradé : LLM down ou timeout → default in_scope (graceful)
            return ScopeResult(
                label="in_scope",
                reason=f"LLM error, default in_scope: {type(e).__name__}",
                via="fallback_in_scope",
                pre_written_response=None,
            )

        parsed = _extract_json(text)
        if not parsed or "label" not in parsed:
            return ScopeResult(
                label="in_scope",
                reason="LLM JSON parse failed, default in_scope",
                via="fallback_in_scope",
                pre_written_response=None,
            )

        label = parsed.get("label", "in_scope")
        reason = parsed.get("reason", "")[:200]
        if label not in ("in_scope", "out_of_scope", "urgent"):
            label = "in_scope"  # safe default

        if label == "urgent":
            return ScopeResult(
                label="urgent",
                reason=reason,
                via="llm",
                pre_written_response=URGENT_RESPONSE,
            )
        if label == "out_of_scope":
            return ScopeResult(
                label="out_of_scope",
                reason=reason,
                via="llm",
                pre_written_response=OUT_OF_SCOPE_RESPONSE,
            )
        return ScopeResult(
            label="in_scope",
            reason=reason,
            via="llm",
            pre_written_response=None,
        )
