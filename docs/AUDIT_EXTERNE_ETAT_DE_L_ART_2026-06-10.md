# Audit externe & état de l'art — OrientAI (2026-06-10)

> Expertise globale du repo `OrientAI` (HEAD `9d9384a`) croisée avec (1) les critères du
> dossier AI Grand Challenge 2026 et (2) une recherche état de l'art mi-2026 sur les
> assistants conversationnels RAG. Objectif : comprendre pourquoi l'IA déçoit ses
> utilisateurs et définir le chemin vers une plateforme prête pour VivaTech.
> Document d'analyse uniquement — aucun changement de code.

---

## 1. Verdict global

Le sentiment « l'IA est plutôt mauvaise » **est corroboré par les propres mesures du
projet** — ce n'est pas un ressenti subjectif :

- Le bench officiel Phase D (2026-05-11) rend un **NO-GO** (Gates 1 et 5 échouées) :
  recall@5 = 0.648 (cible 0.75), rubrique juges 8.18–10.75/18 (cible 12), les **deux**
  juges externes notant OrientAI **sous un Mistral nu** (`docs/BENCHMARK_PHASE_D_2026-05-11.md:314-324,486-487`).
- Faithfulness Ragas mesurée à **0.49 bimodal** : 54 % des réponses extrapolent au-delà
  du corpus. Le repo lui-même la qualifie de **« bloqueur produit n°1 »**
  (`docs/FUTURE_PHASES_2026-05-18.md:37-49`).
- Latences réelles observées en spot-check : 22.7 s, 57.2 s, 78.4 s, **102.3 s**
  (`docs/SPOT_CHECK_V5_2026-05-14-post-q11-fix.md:30,61,231,295`) contre un « p50 6 s »
  annoncé — et un timeout serveur à 30 s qui transforme une partie des requêtes en erreurs.

Le paradoxe : le système est **excellent sur ce qu'il s'interdit** (0 hallucination à
confidence ≥ 0.8 sur 497 réponses, refus adversarial 90-100 %) et **médiocre sur ce
qu'il livre**. L'architecture optimise l'honnêteté au détriment de l'utilité ; or le
concurrent réel — ChatGPT, utilisé par 61 % des terminales pour Parcoursup en 2026 —
gagne précisément par la fluidité. Le créneau défendable d'OrientAI est « la fluidité de
ChatGPT + le sourcing d'Albert » ; le pipeline actuel ne tient ni l'une ni l'autre
promesse en conditions réelles.

---

## 2. Causes racines de l'insatisfaction (preuves repo)

### 2.1 La génération ignore ou dépasse ses sources (cause n°1)
- Bug live « cyber Bretagne » : le retrieval ramène BTS Rennes (rang 6) et BUT Brest
  (rang 7), mais le générateur répond « pas de formation pertinente » et propose la
  **Guadeloupe** (`docs/SESSION_HANDOFF_2026-05-08_VERROUILLAGE.md:134-160`).
- Q11 spot-check : 4 spécialités bac pro listées, **une seule réellement sourcée**, les
  autres générées de mémoire (`docs/SPOT_CHECK_V5_2026-05-14-post-q11-fix.md:374-381`).
- Faithfulness 0.49 : le retrieval a été réparé (4/13 → 9/13 top-5) mais la **génération
  reste le maillon faible** (`docs/FUTURE_PHASES_2026-05-18.md:38`).

### 2.2 Sur-refus et sur-blocage (cause n°2)
- Q12 (« taux réussite L1 ») : retrieval 5/5 fiches pertinentes (~0.99) → le validator
  **BLOQUE** toute la réponse pour cause « bac S supprimé » et sert une redirection
  CIO/ONISEP (`docs/SPOT_CHECK_V5_2026-05-14-post-q11-fix.md:404-417`).
- La policy bloque dès 1 corpus_warning OU 1 règle BLOCKING (`src/validator/policy.py:216,247`).
- Les templates de refus identiques mot-pour-mot ont été perçus comme « placebo »
  (`src/rag/router_llm.py:50-55`) — patch cosmétique, symptôme non traité.
- Le user-test cité dans le code : **3/5 profils ne recommandaient pas l'outil**
  (`src/validator/policy.py:12-15`).

### 2.3 Format sur-contraint (cause n°3)
- Cap R6 ≤ 250 mots, 2-3 puces max (`src/prompt/system_v4_strict.py:108-124`).
  Coût mesuré par les juges : diversité géographique −1.69, découverte −1.52
  (`docs/BENCHMARK_PHASE_D_2026-05-11.md:341-343`).
- Incohérence doc/code : `max_tokens` documenté 400, réel **800** (`src/rag/generator.py:438`).

### 2.4 Latence réelle (cause n°4)
- Cold-start ~14 s non mitigé hors warmup serveur (`docs/FUTURE_PHASES_2026-05-18.md:164-185`).
- 4 appels LLM/embed séquentiels bloquants par requête (Scope → Router → embed → Medium).
- Le streaming SSE existe (`src/api/server.py:655-722`) mais émet les tokens **avant**
  validation (contenu INFIDELE déjà affiché quand le verdict tombe) et sans retry.

### 2.5 Pas de vraie conversation (cause n°5)
- Le système est **single-turn** : l'historique est empilé dans les messages sans
  réécriture de requête ni résolution de coréférence (`src/rag/pipeline.py:345-353`,
  `src/rag/generator.py:413-418`). Le multi-tour (`ConversationState`, Path B) n'a jamais
  été débloqué (`docs/BENCH_GATES.md:79-82`). Or l'orientation est intrinsèquement un
  dialogue long — c'est la promesse centrale du dossier (« conversational »).

### 2.6 Trous de couverture corpus
- recall@5 par catégorie : `reorientation` 0.50, `geographique` 0.60, `live` 0.50
  (`docs/BENCHMARK_PHASE_D_2026-05-11.md:261-265`).
- 4 questions à 0/5 top-5 non résolues : Master Droit PACA, Guadeloupe, Bac pro
  Industrie, doctorat chimie (`docs/FUTURE_PHASES_2026-05-18.md:189-201`).

### 2.7 Dettes structurelles
- 4 stratégies de retrieval coexistantes choisies par cascade de fallbacks
  (`src/rag/pipeline.py:943-1075`) ; constantes magiques empilées.
- Patches ad-hoc « une question = un regex » (Q11 `src/rag/intent.py:388-392`,
  Q9 `src/rag/pipeline.py:543-560`, CROUS `src/rag/pipeline.py:999-1019`) ;
  intent classifier = ~30 listes de regex à l'ordre fragile.
- Code mort sur le chemin prod : retry-with-hint court-circuité en strict_v4
  (`src/rag/pipeline.py:872-880`), `intent_to_format_guidance` inerte.
- Artefacts du bench publié **absents du repo** (`results/bench_v7_v4_1_*` introuvable) ;
  handoff de verrouillage marqué PÉRIMÉ renvoyant à un audit inexistant.
- État mutable global ⇒ `--workers 1` imposé (`src/api/server.py:24,72-74`) — non scalable.

### 2.8 Ce qui est solide (à conserver absolument)
- **0 hallucination haute-confiance** sur 497 réponses (Gate 6 absolu).
- Pré-filtres urgence/détresse avec 3114/3919/119, gratuits et robustes.
- Contrat FactCard JSON + citations `[source SX]` : meilleurs scores juges
  (sourçage +0.86, neutralité +0.53).
- Retrieval hybride dense+BM25+RRF : MRR 0.723 / nDCG 0.725 — quand la fiche est
  trouvée, elle est bien classée.
- Discipline d'évaluation rare : gates définies avant bench, blinding, catégorie `live`.

---

## 3. Écarts vs critères du dossier AI Grand Challenge

| Critère du dossier | État réel | Écart |
|---|---|---|
| « Aucun chiffre sans source » | Tenu sur les chiffres à haute confiance (0 hallu) mais 54 % des réponses contiennent des claims non supportés ; sources fantômes (Q11) | **Majeur** |
| « Refus plutôt que fabrication » | Sur-tenu → sur-refus : blocages alors que la donnée existe (Q12) | **Majeur** (dans l'autre sens) |
| Conversationnel | Single-turn de fait ; pas de mémoire ni réécriture contextuelle | **Majeur** |
| Posture empathique, question ouverte finale | Étouffée par le cap 250 mots et le ton « strict » | Moyen |
| Reformulation du profil (scénario Léo) | Non implémentée (pas de profil utilisateur) | Moyen |
| Latence utilisable | p50 annoncé 6 s ; réel jusqu'à 102 s ; timeouts 504 | **Majeur** |
| Relais humain, briefing, dashboard | Hors périmètre de ce repo (frontend/platform) | À auditer côté plateforme |
| Détection de détresse | Solide (regex + numéros nationaux) | OK |
| Minimisation RGPD, traçabilité sources | Implémentées (logs anonymisés, champ sources) | OK |
| AI Act haut-risque | Bonnes bases ; obligations applicables à partir du 02/12/2027 ; lignes directrices Commission du 19/05/2026 à intégrer | Mineur (documentation) |

---

## 4. État de l'art mi-2026 — synthèse

Recherche complète (sources 2024-2026, URLs dans le rapport d'agent) :

1. **RAG conversationnel** : le standard de production = réécriture/condensation de
   requête par un modèle rapide + mémoire à 2 niveaux (3-5 derniers tours bruts + résumé
   glissant) + profil utilisateur persistant explicite (atout RGPD) + clarification
   proactive quand la requête est sous-spécifiée.
2. **Agentique borné > cascade fixe** : un orchestrateur LLM unique avec tools
   (`semantic_search`, `stat_lookup` SQL, `clarify`) et budget d'itérations plafonné (≤2)
   remplace avantageusement une cascade de classifieurs — qualité multi-hop sans
   l'explosion de latence. C'est le pattern des meilleurs assistants verticaux
   (Sierra, Klarna : 80 %+ de résolution autonome) et du web-search tool d'Anthropic.
3. **Retrieval** : reranker cross-encoder obligatoire (BGE-reranker-v2-m3 auto-hébergé =
   souverain, 50-100 ms) ; contextual retrieval (préfixe contextuel par chunk : −67 %
   d'échecs de retrieval) ; lookups chiffrés via SQL structuré, pas via RAG textuel.
4. **Génération groundée** : citation spans vérifiés (≈92 % de précision de citation
   possible) ; **longueur adaptative à l'intent** — la recherche montre que les caps durs
   uniformes dégradent la satisfaction ; structured outputs.
5. **Latence** : barre 2026 = sub-2 s p95 perçu pour un chat ; leviers par impact :
   streaming (l'optimisation n°1), prompt caching (−85 % latence sur longs prompts),
   semantic caching (31 % des requêtes sémantiquement similaires ; hit rates 60 %+ sur
   les questions récurrentes type « c'est quoi un BUT ? »), modèles rapides (Ministral 3 :
   TTFT 0.5-0.7 s) pour les sous-tâches, parallélisation.
6. **Garde-fous proportionnés** : NLI grounding check **phrase-par-phrase** (flagger ou
   réécrire la phrase non supportée) plutôt que BLOCK global ; mesurer le sur-refus
   (XSTest, OR-Bench) ; détection de détresse par classifieur dédié en parallèle.
7. **Évaluation** : RAGAS corrèle mal avec l'humain (~0.55) ; il faut un golden set
   conversationnel multi-tours co-construit avec des conseillers, de l'A/B en prod, un
   feedback loop (👍/👎) et des LLM-judges calibrés, jamais bruts.
8. **Concurrence** : Hello Charly (1 M de jeunes, intégré Parcoursup, ton ludique
   personnalisé), Albert/DINUM (souverain SecNumCloud, RAG sourcé). ChatGPT domine
   par la fluidité, pas la fiabilité (mauvaise sur Parcoursup).
9. **Stack Mistral 2026** : Mistral Medium 3.5 (génération + function calling +
   structured outputs), Ministral 3 / Small 4 pour les sous-tâches rapides,
   Magistral si raisonnement explicite, `mistral-embed` (top MTEB-French), Mistral OCR 2
   pour structurer les fiches.

### Architecture de référence recommandée
1. **Entrée** : semantic cache (réponses en ms sur les questions récurrentes).
2. **Compréhension** (Ministral 3, parallélisé) : réécriture contextuelle de la requête
   (tours précédents + profil) + intent + distress check.
3. **Orchestrateur agentique borné** (Mistral Medium 3.5) avec tools `semantic_search`
   (hybride + reranker BGE + contextual retrieval), `stat_lookup` (SQL sur indicateurs
   chiffrés — garantit « aucun chiffre sans source »), `clarify` ; ≤ 2 itérations.
4. **Génération groundée streamée** : citation spans, longueur adaptative, ton chaleureux,
   TTFT < 1 s perçu.
5. **Garde-fous post-hoc légers** : NLI phrase-par-phrase sur le flux (flag/réécriture
   ciblée, pas de BLOCK global) ; relais humain/3114 par le distress check.
6. **Transverse** : mémoire 2 niveaux + profil effaçable ; éval conversationnelle,
   A/B, feedback loop ; prompt caching ; hébergement souverain.

---

## 5. Priorités recommandées

### P0 — Quick wins UX (jours → 2 semaines) : « arrêter de perdre l'utilisateur »
1. **Latence perçue** : streaming par défaut côté plateforme ; éliminer le cold-start
   (warmup garanti, instance chaude) ; prompt caching du system prompt ; viser TTFT < 1.5 s.
2. **Désamorcer le sur-blocage** : passer la policy de BLOCK global → WARN ciblé sauf
   fabrication avérée de formation/chiffre ; mesurer le taux de blocage en prod et le
   taux de faux positifs (cas Q12 = bug produit, pas une feature).
3. **Longueur adaptative** : remplacer le cap dur 250 mots par un budget par intent
   (court pour un fait, structuré pour une comparaison/découverte) ; réaligner doc et
   code (`max_tokens`).
4. **Libellés sources lisibles** (bug live #6) et variantes de refus réellement utiles
   (proposer l'alternative la plus proche au lieu d'une redirection sèche).
5. **Fix faithfulness côté prompt** : instruction explicite d'utiliser les sources
   présentes (le bug Bretagne = sources rangs 6-7 ignorées → revoir le top-K transmis
   et l'ordre d'injection des FactCards).

### P1 — Structurel (3-6 semaines) : « devenir vraiment conversationnel et fidèle »
1. **Réécriture de requête contextuelle** (Ministral/Small, < 1 s) + mémoire 2 niveaux +
   profil utilisateur léger — débloque le multi-tour promis par le dossier.
2. **Reranker cross-encoder** (BGE-reranker-v2-m3 auto-hébergé) à la place du reranker
   maison + contextual retrieval sur les fiches.
3. **NLI grounding check phrase-par-phrase** en remplacement progressif du validator
   BLOCK/WARN/PASS global (objectif : faithfulness ≥ 0.8 sans sur-refus).
4. **`stat_lookup` SQL** sur une table structurée des indicateurs (taux d'accès,
   insertion, salaires) — étend le bypass SELECT existant.
5. **Éval conversationnelle** : golden set multi-tours + feedback 👍/👎 en prod +
   mesure du taux de blocage/refus comme métrique produit de premier rang.

### P2 — Refonte (post-VivaTech) : « consolider »
1. **Orchestrateur agentique borné** remplaçant la cascade Scope → Router → intent
   (un seul appel avec tools, ≤ 2 itérations) ; suppression des 4 stratégies de retrieval
   concurrentes et des patches par-question.
2. Couverture corpus ciblée sur les catégories en échec (reorientation, geographique,
   DOM-TOM, bac pro, Parcoursagri) — guidée par les questions `live`.
3. A/B testing et boucle d'amélioration continue ; multi-workers / état partagé pour
   scaler ; conformité AI Act documentée (lignes directrices 19/05/2026).

---

## 6. Limites de cet audit
- Le repo frontend `OrientAI_Platform` (UX, relais conseiller, dashboard, accessibilité
  RGAA) n'était pas accessible dans cette session : les modules 2 et 3 du dossier ne sont
  pas audités ici.
- Les chiffres de bench cités proviennent des documents du repo ; les artefacts bruts du
  bench du 11/05 sont absents du dépôt et n'ont pas pu être re-vérifiés.
