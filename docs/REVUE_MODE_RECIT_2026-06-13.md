# Revue critique - Plan Mode Récit (ordre Jarvis 2026-06-13-1352)

Auteur : Claudette (dev). Phase 0 = revue, aucun code écrit.
Méthode : lecture du code réel (pas le briefing seul) - pipeline.py, factory.py,
generator.py, scope_classifier.py, judge.py, server.py, schemas.py, les 2 tools
"dormants", + sondes corpus (formations.json 52 040 fiches).
Objectif : contre-propositions point par point PUIS plan d'implémentation à
contre-auditer avant GO build.

---

## TL;DR (à lire en premier)

1. **Le plan reconstruit ce qui existe déjà.** `src/agent/pipeline_agent.py`
   (AgentPipeline, Sprint 4, ADR-051) chaîne DÉJÀ ProfileClarifier ->
   QueryReformuler -> retrieval multi-query parallèle -> aggregation -> generate,
   avec tests + benchmarks. Le plan traite ces tools comme "dormants à câbler" ;
   c'est un système complet benchmarké. Réutiliser/adapter, ne pas reconstruire.

2. **La preuve empirique du plan est mal attribuée.** Le "aucun salaire dans mes
   sources" du récit prod n'est PAS (principalement) de la dilution sémantique.
   C'est un BUG de clé confirmé : `generator._insertion_line()` lit `f["insertion"]`
   (None sur tout le corpus migré 12/06) alors que salaire + taux d'emploi vivent
   dans `f["insertion_pro"]` (15 172 formations concernées). Fix ~2 lignes,
   orthogonal au mode récit, à faire AVANT et à mesurer séparément.

3. **Plusieurs garde-fous du plan sont déjà satisfaits par construction.**
   scope_classifier tourne déjà en 1er (détresse avant tout) ; le contrat API
   `history[]` est déjà câblé bout en bout (R2 backend quasi fait) ; le mécanisme
   "few-shot golden = ton/structure, chiffres ignorés" existe déjà (réutilisable
   pour le registre conseil-cadré).

4. **Ne PAS étendre `judge.py`** (mandate 4) : c'est le juge comparatif
   longitudinal protégé (Run F+G). Instrument récit = module SÉPARÉ, isolé par
   construction (les 497q ne déclenchent jamais le mode récit).

5. **Latence : risque réel.** scope (LLM) + RouterLLM (LLM) + extraction profil
   (LLM) + génération longue (+ retry) peut dépasser 15s. Décision d'archi
   nécessaire : en mode récit, l'extraction profil REMPLACE le RouterLLM.

6. **Calendrier honnête : R1 core = 2-3 jours soignés.** Gel dimanche soir 14/06
   très ambitieux si on part aujourd'hui après revue. Réaliste pour VivaTech
   (17/06) : mode récit MONO-TOUR sous flag + gates détresse durs. R2 multi-tour
   parqué post-VivaTech.

---

## Mandate 1 - Pièges repo

### P1. DUPLICATION : l'AgentPipeline existe déjà (CRITIQUE)
`src/agent/pipeline_agent.py` implémente exactement l'archi du plan :
`query -> ProfileClarifier -> QueryReformuler -> retrieval FAISS parallèle par
sub-query -> aggregation cross-corpus (dedupe + top-N) -> generate`.
Artefacts associés : `tests/test_agent_profile_clarifier.py`,
`test_agent_query_reformuler.py`, `test_agent_cache.py`,
`scripts/bench_profile_clarifier_medium_vs_large.py`,
`scripts/run_bench_agent_pipeline.py`, `scripts/test_*_integration.py`.
Baseline bench documentée (39.4% verified / 17.9% halluc). ADR-051 = rationale.
=> Le plan doit explicitement statuer : on REBRANCHE/adapte l'AgentPipeline, ou on
réimplémente une branche récit dans `OrientIAPipeline` (la prod). Reconstruire de
zéro = dette + perte du travail Sprint 1-4.

### P2. Deux pipelines coexistent
La prod sert `make_production_pipeline()` -> `OrientIAPipeline` (pipeline.py), qui
NE PASSE PAS par l'agentique. L'AgentPipeline (agent/) est un monde parallèle non
servi. Le mode récit doit choisir son point d'insertion :
- (a) branche récit DANS `OrientIAPipeline._prepare_for_generation` (cohérent avec
  scope/router/select/golden_qa déjà là), OU
- (b) flag qui dispatche vers AgentPipeline pour les récits.
Recommandation : (a). On reste dans le pipeline prod instrumenté (Langfuse,
validator, post_process, geo_coherence) et on réutilise ProfileClarifier +
QueryReformuler comme COMPOSANTS, pas l'AgentPipeline comme orchestrateur.

### P3. scope_classifier tourne DÉJÀ en premier (garde-fou détresse satisfait)
`_prepare_for_generation` (pipeline.py:457) appelle `scope_classifier.classify`
AVANT router/select/retrieve/generate. Si la branche récit s'insère après le
short-circuit scope, "détresse avant branche récit" est satisfait par construction.
MAIS attention : le regex urgent ne couvre QUE suicide/violences explicites
(scope_classifier.py:53-70). "je sers à rien" / "je tiens plus" NE matchent PAS le
regex -> ils reposent ENTIÈREMENT sur le LLM Mistral-small. Pour un récit 300+ chars
qui noie le signal, c'est une question de COMPORTEMENT LLM, pas d'archi. Le gate
R06/R07 doit le tester empiriquement (cf mandate 6).

### P4. RouterLLM tourne aussi après scope (chevauchement + latence)
`_prepare_for_generation` (pipeline.py:489) appelle RouterLLM qui produit DÉJÀ
FilterCriteria, domain_lock, top_k_override, refusal_reason, hardlock - via un appel
LLM Mistral-small. C'est un chevauchement direct avec "détection mode récit" +
"extraction profil". Empiler scope + router + profil = 3 appels LLM séquentiels
avant génération -> budget <15s menacé.
=> DÉCISION D'ARCHI : en mode récit, l'extraction profil REMPLACE le RouterLLM
(le profil + multi-query EST le routing). Sinon paralléliser scope+profil.

### P5. BUG salaire/insertion confirmé - root cause != dilution (CRITIQUE)
- Corpus migré le 12/06 (backup `formations.json.bak-presalary-20260612-085000`).
- `f["insertion"]` = None sur 100% du corpus actuel. Écrit uniquement par
  `src/collect/insersup.py:370` (ancien chemin).
- Données réelles : `f["insertion_pro"]` (dict) présent sur **15 172 formations**,
  avec clés salaire (`salaire_net`, `salaire_median_embauche`,
  `salaire_brut_median_annuel`, `salaire_q1`, `salaire_q3`) + taux_emploi_6/12/18m.
- `generator._insertion_line()` (generator.py:225,239) lit `f.get("insertion")` et
  `ins.get("salaire_median_12m_mensuel_net")` -> les DEUX clés sont absentes du
  corpus migré -> retourne None pour les 15 172 fiches -> salaire ET taux d'emploi
  ne remontent JAMAIS dans le contexte LLM.
- Conséquence : "aucun salaire dans mes sources" était HONNÊTE et CORRECT. La fiche
  MIAGE Lille a son salaire dans `insertion_pro` (pas de hop PCS nécessaire pour les
  formations), mais le generator ne sait pas le lire.
- L'autre source salaire (`insee_salaire`, 59 fiches PCS-keyed,
  `salaire_net_median_mensuel`) est un fallback métier-level (hop
  formation->métier->ROME->PCS). Cf mémoire "routing salaire -> INSEE PCS".
=> ACTION : fix ~2 lignes de `_insertion_line` (lire `insertion_pro` + mapper les
nouvelles clés salaire) AVANT toute archi récit. À mesurer séparément. Ne PAS faire
du salaire MIAGE un critère de succès du mode récit (attribution faussée - cf leçon
validate_measurement_instrument 11/06).

### P6. golden_qa few-shot = mécanisme "Comment/Quoi" réutilisable
`_maybe_build_golden_qa_prefix` (pipeline.py:1767) injecte top-1 Q&A golden en
few-shot avec séparation stricte : la Q&A = référence ton/structure, ses
écoles/chiffres IGNORÉS, seules les fiches RAG = sources autorisées
(generator.py:403-408, injection system-side). C'est EXACTEMENT le mécanisme dont le
plan a besoin pour "reformulation/pourquoi-toi = registre conseil-cadré non compté
unsupported". MAIS le golden_qa actuel exemplifie des réponses COURTES -> en mode
récit il faut un few-shot DÉDIÉ au format sectionné, sinon il tire la sortie vers le
court (leçon prompt_additive : le few-shot doit matcher le format de sortie réel).

### P7. max_tokens : le format long ne tient pas dans le cap actuel
v4 strict cap `max_tokens=800` (generator.py:438) + R6 "max 250 mots" (soft target).
v3.2 legacy : pas de cap. Un format sectionné niveau conseiller (reformulation +
2-4 pistes argumentées + vigilance + étape) = 600-900 mots ~ 1200-1500 tokens.
=> Le mode récit DOIT avoir : un nouveau system prompt (ni v4_strict ni v3.2), un
nouveau branch dans `_build_chat_kwargs`, max_tokens relevé (~1500), bypass du cap
250 mots. Vérifier compat avec le strip `<reponse_finale>` (generator.py:649).

### P8. Retrieval annexe = le vrai point dur (faire remonter insee_salaire/insertion)
Le retrieval prod = Option C v6 (k=150, séparation main/annex, quota adaptatif max 3
annexes dans le top-K, seuil score 0.6) OU quad-subindex si RouterLLM route
(pipeline.py:74-102, 965+). Les corpora annexes remontent mal (ADR-058 : textes
annexes mal alignés sémantiquement, dette technique actée). Or insee_salaire /
insertion_pro (domain) SONT des annexes. Le multi-query récit doit fusionner
proprement avec ce mécanisme - et c'est précisément là que ça peut échouer. Bonne
nouvelle : après fix P5, l'essentiel du salaire/insertion est SUR la fiche formation
(insertion_pro field), donc pas besoin de remonter l'annexe pour ces faits-là.

### P9. history déjà câblé bout en bout (R2 backend quasi fait)
`AnswerRequest.history` (schemas.py:53) : list[HistoryMessage], max 6 messages,
content max 3000 chars, default None (rétrocompat). `server.answer` forwarde
(server.py:418-431). `scope_classifier.classify(history=...)` + `generate(history=...)`
le consomment. Donc R2 "contrat étendu body.history[]" est DÉJÀ FAIT côté backend
(et le cap est 6, pas 4). Gap réel R2 = (a) la plateforme Next.js doit ENVOYER
l'history, (b) logique d'accumulation profil sur les tours + autorater suffisance.

---

## Mandate 2 - Schéma profil

ProfileClarifier existant (`Profile`) : `age_group` (11 enums), `education_level`
(10 enums), `intent_type` (10 enums), `sector_interest[]`, `region`,
`urgent_concern`, `confidence`, `notes`. Enum-validé (`is_valid()`), testé, mappé
aux domain hints reranker, cache LRU.

Gaps RÉELS du plan vs existant (à ajouter) :
- `a_eviter: list[str]` - ABSENT de Profile. Vrai manque, central pour R01/R02/R09.
- `contraintes: {alternance: bool|null, duree_max|null}` - ABSENT. Utile R03/R05.
- `mobilite` (dans geo) - ABSENT.

Champs du plan redondants avec l'existant (à NE PAS dupliquer) :
- `cible.type = libre|domaine|etude|metier` recouvre largement `intent_type`.
- `situation_actuelle.type` recouvre `age_group` + `education_level`.

Recommandation : **ÉTENDRE `Profile` existant** (ajouter a_eviter, contraintes,
mobilite ; garder les enums fermés = anti-dérive) plutôt que créer un schéma neuf.
- Span-grounding (le plan veut chaque valeur ancrée dans le texte) : le
  function-calling Mistral ne garantit pas les spans nativement. Options : (a)
  ajouter un champ `evidence` par facette dans le schéma tool, ou (b) best-effort +
  validation post (le terme extrait doit apparaître dans le texte source). Je
  recommande (b) pour le MVP (déterministe, pas de dépendance au LLM pour la
  fidélité du span).
- ProfileClarifier utilise `mistral-large-latest` (lent ~2s, cher) et PAS temp=0.
  Pour le budget latence : passer `mistral-small` ou `medium` + temp=0. À benchmarker
  (le bench medium-vs-large existe déjà : `bench_profile_clarifier_medium_vs_large.py`).

Faisabilité côté fiches (vérifié) : exclusion a_eviter réalisable sur `domaine` +
`debouches[].libelle` (présents) ; geo sur `region` (~81% des formations) / `ville` /
`geopoint`. OK.

---

## Mandate 3 - Template requêtes déterministe vs LLM libre

Le plan veut un TEMPLATE déterministe (1 requête/facette + step-back). Arguments :
reproductibilité, isolation baseline, zéro coût/latence LLM, zéro dérive. Valides.

CONTRE-ARGUMENT (fort) : `query_reformuler.py` (LLM, tool_choice=any) fait ce qu'un
template NAÏF ne peut pas - router chaque sub-query vers le BON corpus
(insee_salaire, insertion_pro, apec_region, metier_prospective) avec le vocabulaire
qui ACTIVE le domain hint (query_reformuler.py:247-263). Un template "1 requête par
facette" génère des requêtes génériques qui tapent le corpus formation et MANQUENT
les annexes. La dilution est en partie un problème de ROUTING corpus, pas seulement
de longueur (cf P5/P8). Donc un template "1/facette" risque de recréer le miss
annexe.

Recommandation : **template CORPUS-AWARE déterministe** (pas "1/facette" naïf). Le
template encode le mapping facette -> corpus + vocabulaire domain-hint :
- intérêt/cible étude -> requête `formation` (vocab existant)
- cible métier -> requête `metier` + `insertion_pro`
- rémunération implicite -> requête `insee_salaire` avec libellé métier
- géo -> boost (pas filtre dur, cf plan, OK)
- a_eviter -> exclusion post-rerank
- + 1 step-back (abstraction)
On garde le déterminisme/reproductibilité ET le routing corpus. C'est en gros
query_reformuler "figé en code" plutôt qu'en LLM.

Alternative : réutiliser query_reformuler LLM tel quel (déjà testé) en `mistral-small`,
le déterminisme baseline étant préservé par le flag (les 497q ne déclenchent jamais
le récit). Je penche pour le template corpus-aware POUR le budget latence (on a déjà
scope + éventuel profil en amont).

---

## Mandate 4 - Extension rubrique juge

`src/eval/judge.py` = juge COMPARATIF 6 critères (neutralité, réalisme, sourçage,
diversité_geo, agentivité, découverte ; 0-3 ; total /18), blindé A-G, LONGITUDINAL
(Run 1 -> F+G). Fichier PROTÉGÉ (CLAUDE.md : "Préservé pour comparaison
longitudinale").

Réponse nette : **étendre judge.py CASSE la comparabilité 497q/Run F+G. NON.**

Recommandation : **instrument SÉPARÉ** pour la famille narrative (ex
`src/eval/judge_narrative.py`). Comparabilité préservée par construction : le mode
récit est isolé (>=300 chars), les 497q ne le déclenchent jamais -> elles continuent
d'être jugées par judge.py inchangé.
Rubrique récit : groundedness_faits (réutilise la logique validator/fact_check :
chiffres uniquement sourçables) + couverture_facettes (vs profil extrait) +
zero_fiche_evitee (a_eviter respecté) + reformulation_ouverture (montre qu'il a
compris). Le registre conseil-cadré NON compté unsupported (réutilise la distinction
Comment/Quoi du golden_qa, P6).
Groundedness "section faits >= baseline" : le pipeline expose déjà
`last_validation.honesty_score` (faithfulness) ; on peut l'appliquer à la SECTION
faits isolée. Réutilisable.
IMPÉRATIF : valider l'INSTRUMENT sur 5 cas étiquetés main AVANT toute mesure (leçon
validate_measurement_instrument 11/06). Le juge narratif doit aussi tourner temp=0 +
sur sources figées (leçon gate_noise : temp=0 pas déterministe côté serveur Mistral
+ retrieval -> prédicat déterministe sur sources figées pour le set démo).

---

## Mandate 5 - Effort honnête + ce qui se parque

R1 :
- 1a détection récit déterministe + tests : FAIBLE (2-3h). Longueur + lexique facettes.
- 1b extraction profil : MOYEN si on ÉTEND ProfileClarifier (3-4h : +a_eviter/
  contraintes/mobilite, span best-effort, switch model small+temp0, tests). ÉLEVÉ si
  reconstruction (1j+) -> ne pas reconstruire.
- 1c retrieval multi-query : MOYEN-ÉLEVÉ (4-6h). Template corpus-aware + fusion avec
  annex quota + exclusion a_eviter + tests. Point dur = faire remonter les annexes
  (ADR-058) - atténué par le fix P5 qui met salaire/insertion sur la fiche formation.
- 1d génération prompt dédié sectionné + max_tokens + few-shot récit : MOYEN (4-5h).
  Nouveau system prompt, branch _build_chat_kwargs, few-shot sectionné, compat strip
  XML, tests truncation.
- 1e flag ORIENTIA_NARRATIVE_MODE default OFF : FAIBLE (1h).
- juge narratif + validation instrument (5 cas main) : MOYEN (3-4h).
- **R1 total réaliste : 2-3 jours dev soignés.** Ne tient pas pour un gel dimanche
  soir 14/06 si on démarre aujourd'hui 13/06 après revue.

R2 (multi-tour) : backend history DÉJÀ là (P9). Reste : accumulation profil sur tours
+ autorater suffisance (réutilise un autorater existant) + plateforme envoie history.
MOYEN côté backend (3-4h), dépend de la plateforme (zone bridge).

R3 (run famille narrative + golden CI + spot-check Matteo + arbitrage flag) :
run + analyse (~0.5j) + spot-check humain.

CE QUI SE PARQUE si débordement (priorité = démo VivaTech 17/06, flag ON jour J) :
- R2 multi-tour -> post-VivaTech (le mono-tour récit a déjà la valeur démo).
- juge narratif full -> spot-check humain Matteo suffit pour la démo.
- span-grounding strict -> best-effort.
- exclusion a_eviter sophistiquée (ROME codes) -> mots-clés simples + domaine.
- routing annexe avancé -> on s'appuie sur le fix P5 (faits sur la fiche).

PRIORITÉ démo : fix P5 (salaire/insertion) + 1a + 1b(étendu) + 1c(template
corpus-aware) + 1d(sectionné + max_tokens) sous flag, validé sur les 5 récits
paramétriques + gates détresse durs.

Recommandation calendrier : viser un mode récit MONO-TOUR sous flag pour VivaTech,
R2 parqué. Gel dimanche soir = ambitieux ; gel réaliste = R1 core stabilisé +
gates verts, R2 ensuite.

---

## Mandate 6 - Validation seed 10 récits

5 paramétriques : bien conçus.
- R01 (cas prod foiré, non-régression) : bon. MAIS attention au critère salaire (cf
  P5) : exiger taux_emploi (74.7% est SUR la fiche, surfacable après fix P5) +
  honnêteté si salaire absent ; ne PAS exiger un chiffre salaire tant que P5 +
  routing pas validés isolément.
- R02-R05 : OK.

5 adversariaux (gates) :
- R06 (détresse explicite "je sers à rien") : "je sers à rien" n'est PAS dans le
  regex urgent -> repose sur le LLM scope. Bon cas. Vérifier que le LLM tire `urgent`
  quand le signal est noyé dans 300+ chars d'orientation.
- R07 (détresse subtile "je tiens plus") : idem LLM-only, le plus dur. Garder.
- R08 (hors-scope déguisé "écris mon mémoire") : à tester - le scope_classifier
  pourrait juger `in_scope` à cause du contexte orientation autour. Faux in_scope
  possible. Bon cas piège.
- R09 (contradictoire dev mais évite programmer) : bon, teste a_eviter + non-hallu.
- R10 (ultra-vague >300 chars) : bon, teste relance vs réponse à vide.

Manques à ajouter :
- +1 récit avec question rémunération EXPLICITE -> expose le linkage salaire au
  grand jour, mesure l'honnêteté (et valide le fix P5).
- +1 CAS CONTRÔLE détresse négatif : stress d'orientation noyé qui NE DOIT PAS
  escalader (anti faux-positif). Sans symétrie, on optimise l'escalade au prix du
  sur-refus. Le scope_classifier documente déjà ce risque (prompt lignes 232-251).
- (optionnel) +1 récit multi-géo/mobilité -> teste geo en boost, pas filtre dur.

---

## Mandate 7 - Plan d'implémentation détaillé (à contre-auditer avant GO)

Ordre proposé, fichiers touchés, tests, points de gel.

### Étape 0 (PRÉ-REQUIS, hors mode récit) - fix bug salaire/insertion
- `src/rag/generator.py:_insertion_line` : lire `f.get("insertion_pro")` (fallback
  `f.get("insertion")` pour rétrocompat) ; mapper `salaire_net` /
  `salaire_median_embauche` / `salaire_brut_median_annuel` + `taux_emploi_12m`.
- Tests : `tests/test_generator.py` (une fiche insertion_pro -> ligne émise).
- Mesure ISOLÉE : sonde MIAGE Lille (mode classique) -> le salaire/taux remonte.
- Gel : commit dédié `fix:`, PR séparée, mergeable indépendamment (pattern auto-merge
  outillage/fix ciblé). NE PAS mélanger au mode récit.

### Étape 1 - détection mode récit (déterministe)
- Nouveau `src/rag/narrative_detect.py` : `is_narrative(question) -> bool` (len>=300
  OU >=2 facettes lexicales). Lexique facettes = liste figée (situation/cible/géo/
  évite/contrainte).
- Insertion dans `_prepare_for_generation` APRÈS le short-circuit scope, AVANT
  RouterLLM. Si récit ET flag ON -> branche récit (qui REMPLACE le RouterLLM, P4).
- Tests : les 497q (max ~161 chars) ne déclenchent jamais ; les 10 récits déclenchent.
- Gel : isolation baseline garantie par test.

### Étape 2 - extraction profil (étendre l'existant)
- Étendre `Profile` (a_eviter, contraintes, mobilite) ; model `mistral-small`/medium
  + temp=0 ; span best-effort + validation post.
- Fallback silencieux : échec extraction -> chemin classique (le récit ne dégrade
  jamais sous l'actuel).
- Tests : `tests/test_agent_profile_clarifier.py` étendu + cas null (facette absente).

### Étape 3 - retrieval multi-query corpus-aware
- Template déterministe facette -> sous-requêtes corpus-ciblées (réutilise le vocab
  domain-hint de query_reformuler). Fusion union + dédup + MMR + boosts existants +
  quota annexe. Exclusion a_eviter post-rerank (domaine + libellés débouchés).
- Réutiliser `parallel_apply` (agent/parallel.py) pour les retrievals.
- Tests : couverture facettes -> sources ; a_eviter -> fiche exclue ; non-régression
  retrieval classique.

### Étape 4 - génération sectionnée
- Nouveau system prompt récit (`src/prompt/system_narrative.py`) : 4 sections (Ta
  situation / Pistes / Vigilance / Prochaine étape). Règles R6-R9 INCHANGÉES pour la
  section faits (gouvernent les chiffres cités).
- Branch dans `_build_chat_kwargs` (param `narrative_mode`) : prompt dédié, max_tokens
  ~1500, pas de cap 250 mots, few-shot récit dédié (format sectionné) via le mécanisme
  golden_qa Comment/Quoi.
- Compat strip `<reponse_finale>`.
- Tests : pas de troncature sur réponse longue ; sections présentes ; prompt classique
  + R6-R9 + 497q intacts (non-régression).

### Étape 5 - flag + gates
- `ORIENTIA_NARRATIVE_MODE` default OFF (factory + env).
- juge narratif séparé + validation instrument (5 cas main).
- Gates R1 : groundedness section faits >= baseline ; couverture facettes >=90% ;
  a_eviter 100% ; détresse noyée 100% escalade (NON négociable) + cas contrôle
  négatif ; 497q intactes + golden CI verte (`data/golden_eval/golden_50.json`) ;
  latence <15s à chaud (à surveiller vu P4).

### Étape 6 (R2, parquable) - multi-tour
- Accumulation profil sur tours + autorater suffisance. Backend history déjà prêt
  (P9). Coordonner avec la plateforme (via Jarvis) pour l'envoi de history[].

---

## Questions ouvertes pour Matteo (avant GO)

1. Archi : on insère la branche récit dans OrientIAPipeline (recommandé) et on
   réutilise ProfileClarifier/QueryReformuler comme composants - OK ?
2. Le fix salaire (Étape 0) part en PR séparée mergeable tout de suite - OK ?
3. Template corpus-aware déterministe (recommandé) vs réutiliser query_reformuler LLM
   en small - lequel ?
4. Calendrier : on acte mode récit MONO-TOUR sous flag pour VivaTech, R2 parqué - OK,
   ou tu tiens au gel complet dimanche soir (= scope à réduire) ?
5. [RÉSOLU par Claudette, lookup repo] La "batterie 497q" = conflation. Le set de
   GÉNÉRATION non-régression est `src/eval/questions.json` = 100 questions (médiane
   67 chars, max 118, ZÉRO >=300 chars -> isolation baseline du récit confirmée et
   plus forte qu'annoncé). Le "497" = un compte de RÉPONSES (Phase D fact-check,
   100q x systèmes), pas un set de questions. Gates non-régression : `src/eval/
   questions.json` (100q génération via run_real_full.py:60) + `data/golden_eval/
   golden_50.json` (50q golden CI).
