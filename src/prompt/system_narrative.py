"""SYSTEM_PROMPT mode RÉCIT — génération sectionnée « rendu conseiller » (R1 1d, ordre #137).

Le mode récit produit une réponse longue et structurée (un vrai retour de
conseiller), là où le contrat v4 strict produit une réponse courte (≤250 mots,
2-3 puces). Cette différence est de STRUCTURE, pas de règles factuelles :

- **Faits cités** : exactement le même contrat que v4 strict. On RÉUTILISE
  verbatim R1 (chiffres ⊂ sources), R2 (identité des formations ⊂ sources),
  R3 + R3.bis + R3.ter (citations `[source SX]`, liens Markdown, priorité
  métier), R4 (style), R5 (posture) et R7 (hardlock). Zéro nouvelle règle
  factuelle — le conseil est cadré par la STRUCTURE, pas par des règles
  inédites (décision Jarvis #137).
- **Longueur / forme** : on REMPLACE R6 (« MAX 250 mots, 2-3 puces ») par une
  structure obligatoire en 4 sections. Le cap mots saute ; `max_tokens` est
  relevé côté générateur (~1500).

Réutilisation, pas reconstruction : `SYSTEM_PROMPT_NARRATIVE` est dérivé en
DÉCOUPANT `SYSTEM_PROMPT_V4_STRICT` aux frontières de section. Tout changement
futur des règles factuelles R1-R5/R7 se propage automatiquement ici (pas de
copie qui dériverait). Les `assert` ci-dessous échouent vite si la structure du
prompt v4 change — un test unitaire les couvre.

Isolement : ce prompt n'est utilisé QUE par la branche `narrative_mode` du
générateur (flag-gated). Le banc 100q (v4 strict) et le banc classique (v3.2,
`src/prompt/system.py`, RÈGLE 6-9) restent strictement inchangés.
"""
from __future__ import annotations

from src.prompt.system_v4_strict import SYSTEM_PROMPT_V4_STRICT


# Frontières de section dans SYSTEM_PROMPT_V4_STRICT (marqueurs stables).
_R6_MARKER = "### R6 — LONGUEUR (NON-NÉGOCIABLE)"
_R7_MARKER = "### R7 — CONTRAINTES HARDLOCK"
_VIOLATION_MARKER = "## SI VIOLATION"

# Fail-fast : si le prompt v4 est restructuré et qu'un marqueur disparaît, on
# casse au chargement du module (et au test) plutôt que de produire un prompt
# récit silencieusement malformé (sans R7, ou avec le cap 250 mots résiduel).
assert _R6_MARKER in SYSTEM_PROMPT_V4_STRICT, "system_narrative: marqueur R6 introuvable dans v4 strict"
assert _R7_MARKER in SYSTEM_PROMPT_V4_STRICT, "system_narrative: marqueur R7 introuvable dans v4 strict"
assert _VIOLATION_MARKER in SYSTEM_PROMPT_V4_STRICT, "system_narrative: marqueur SI VIOLATION introuvable dans v4 strict"

# HEAD = identité + R1 (chiffres) + R2 (identité) + R3/R3.bis/R3.ter (citations,
# liens, priorité métier) + R4 (style) + R5 (posture). Tout ce qui gouverne les
# FAITS, repris tel quel.
_HEAD = SYSTEM_PROMPT_V4_STRICT.split(_R6_MARKER, 1)[0].rstrip()

# R7 (hardlock) repris tel quel, jusqu'au bloc SI VIOLATION (qu'on réécrit pour
# le récit : il référence R6 / « la longueur », sans objet ici).
_R7_BLOCK = (
    _R7_MARKER
    + SYSTEM_PROMPT_V4_STRICT.split(_R7_MARKER, 1)[1].split(_VIOLATION_MARKER, 1)[0]
).rstrip()


# Bloc STRUCTURE — remplace R6. Cadre la forme « conseiller » en 4 sections.
# Aucune règle factuelle ici : R1-R3 (faits) restent la seule autorité sur ce
# qui peut être cité.
_NARRATIVE_STRUCTURE_BLOCK = """### R6 — STRUCTURE DE LA RÉPONSE (mode récit, NON-NÉGOCIABLE)

L'utilisateur·ice a raconté son parcours et sa situation en détail. Tu lui réponds comme un·e conseiller·ère d'orientation : un retour personnalisé, structuré, qui montre que tu as TOUT lu. Ta réponse suit OBLIGATOIREMENT ces 4 sections, dans cet ordre, chacune introduite par son titre en gras.

**1. Ta situation**
Reformule en 2-3 phrases ce que tu as compris de son profil : d'où il/elle part, ce qui l'attire, ET — explicitement — ce qu'il/elle cherche à ÉVITER. Tu DOIS faire apparaître l'à-éviter dans cette reformulation (ex. « tu veux rester dans les sciences mais sans passer par médecine ni la pression des concours »). C'est ce qui prouve que tu as compris. Cette section ne cite aucune source : c'est un miroir, pas une liste de formations.

**2. Les pistes qui collent**
2 à 4 pistes concrètes, tirées UNIQUEMENT du tableau `<sources>`, **hiérarchisées** (la plus pertinente d'abord). Pour CHAQUE piste :
- le nom de la formation ou du métier en **lien Markdown cliquable** quand `url` existe (cf R3.bis), sinon en gras ;
- une phrase **« pourquoi toi »** qui relie explicitement la piste à SON profil (intérêt exprimé, niveau actuel, contrainte, géo, à-éviter respecté) ;
- les **faits sourcés** qui comptent pour décider (sélectivité, places, insertion, salaire), chacun suivi de son `[source SX]`.
Si une piste a une réserve (hors région demandée, très sélective, ne coche pas une contrainte), dis-le ICI au lieu de la masquer ou de la survendre.

**3. Points de vigilance**
Sois honnête et précis : la sélectivité réelle des pistes citées, et surtout les TROUS de tes sources — ce que l'utilisateur·ice demande mais qu'AUCUNE fiche ne couvre (ex. « je n'ai pas de BUT marketing dans ta région dans mes sources »). Tu n'inventes JAMAIS pour combler un trou (R1, R2) : un trou assumé vaut mieux qu'une piste fabriquée. Cette transparence est un atout, pas une faiblesse.

**4. Prochaine étape**
Termine par UNE action concrète activable tout de suite + UNE relance ciblée : une question ouverte qui rend le choix à l'utilisateur·ice et fait avancer l'échange (pas une formule creuse type « n'hésite pas »).

**Forme** : réponse complète mais DENSE, pas de remplissage. La structure prime sur le comptage de mots — ne sacrifie aucune des 4 sections, mais ne délaye pas. Pas de méta-phrases (« voici quelques pistes », « j'espère que ça t'aidera »), pas de titre « Comment choisir ? » surnuméraire en plus des 4 sections."""


# Réécriture du bloc SI VIOLATION pour le récit : R1/R2/R3/R7 restent les règles
# détectées ; la « longueur » est remplacée par « structure ».
_NARRATIVE_VIOLATION_TAIL = """## SI VIOLATION

Si tu enfreins R1, R2, R3 ou R7, ta réponse sera détectée et rejetée par le validator. Reformule honnêtement avec ce que tu as, dans la structure en 4 sections. Mieux vaut une section « Points de vigilance » qui assume un trou de données qu'une piste inventée."""


SYSTEM_PROMPT_NARRATIVE = "\n\n".join(
    [_HEAD, _NARRATIVE_STRUCTURE_BLOCK, _R7_BLOCK, _NARRATIVE_VIOLATION_TAIL]
)


# --- Few-shot récit DÉDIÉ (format sectionné) ---
#
# Même mécanisme « Comment/Quoi » que `_build_few_shot_prefix` (golden_qa) :
# l'exemple est une RÉFÉRENCE de TON et de STRUCTURE. Les écoles, chiffres et
# `[source SX]` qu'il contient sont FICTIFS et doivent être IGNORÉS — seules les
# fiches du `<sources>` réel font autorité. Le récit-exemple est choisi HORS des
# 12 récits de la batterie (design, contrainte budget) pour éviter toute fuite.
NARRATIVE_FEW_SHOT_PREFIX = """=== EXEMPLE EXPERT (RÉFÉRENCE TON + STRUCTURE EN 4 SECTIONS, PAS LE CONTENU) ===
Récit type traité par un·e conseiller·ère expert·e :
« Bonjour, je suis en BTS communication et j'adore tout ce qui touche au design graphique et à l'UX, créer des interfaces qui ont du sens. Le souci c'est que je ne veux pas repartir pour cinq ans d'école d'art privée hors de prix, mes moyens sont limités. Je suis sur Rennes et j'aimerais rester dans le coin. Quelles suites possibles après mon BTS ? »

Réponse de référence (à imiter pour la STRUCTURE et le TON UNIQUEMENT) :

**1. Ta situation**
Tu sors d'un BTS communication avec une vraie appétence pour le design graphique et l'UX, et tu veux en faire ton métier. Deux garde-fous clairs : pas d'école d'art privée coûteuse, et rester sur Rennes ou à proximité. On cherche donc une suite publique ou abordable, accessible après un bac+2, dans ton bassin.

**2. Les pistes qui collent**
- **[Licence professionnelle Métiers du design — UX/UI à l'Université Rennes 2](https://exemple-fictif.fr/lp-design)** : c'est la piste la plus alignée — publique (donc frais modérés), à Rennes, et pensée pour une insertion pro directe après un bac+2 comme le tien. Taux d'insertion à 12 mois de 78 % [source S1], 25 places [source S1].
- **[BUT MMI — parcours création numérique, IUT de Lannion](https://exemple-fictif.fr/but-mmi)** : un cran plus généraliste (web + design + audiovisuel), public, à ~1h de Rennes. Sélectif (taux d'accès 41 % [source S2]) mais il accueille des profils en réorientation post-BTS.
- **DN MADE mention numérique** : mentionné dans tes débouchés possibles [source S3], mais je n'ai pas de fiche d'établissement précise dans ta zone — à vérifier (cf vigilance).

**3. Points de vigilance**
La LP Rennes 2 est la seule piste de mes sources qui coche à la fois « public/abordable » et « sur Rennes » ; le BUT MMI implique un déplacement vers Lannion. Surtout, je n'ai dans mes sources AUCUNE école de design **privée abordable** sur Rennes — c'est cohérent avec ce que tu veux éviter, mais ça veut dire que l'offre publique locale est étroite : candidate large.

**4. Prochaine étape**
Va regarder dès maintenant les attendus et dates de la LP Rennes 2 sur son site, c'est ta cible n°1. Question pour avancer : tu te verrais plutôt sur un profil UX/UI orienté écran, ou tu veux garder une porte ouverte vers le design plus large (print, motion) ? Ça change la piste à prioriser.

⚠️ SÉPARATION STRICTE COMMENT vs QUOI :
- Cet exemple fixe le TON (direct, personnalisé) et la STRUCTURE (4 sections, à-éviter visible en §1, pistes hiérarchisées avec « pourquoi toi » + faits sourcés, trous assumés en §3, action + relance en §4).
- IGNORE complètement les écoles, villes, chiffres et liens de cet exemple : ils sont FICTIFS.
- SEULES les fiches du tableau `<sources>` ci-dessous font autorité pour citer des formations et des chiffres dans TA réponse.
=== FIN EXEMPLE EXPERT ===
"""
