# Livrable 2 - Audit complet de l'existant OrientAI

**Auteur :** Claudette (agent dev)
**Date :** 2026-06-08
**Commande :** ordre Jarvis 2026-06-08-1037 (refonte IA idéale + audit + roadmap VivaTech)
**Périmètre :** deux repos, `~/projets/OrientIA` (coeur LLM/RAG) et `~/projets/OrientAI_Platform` (front Next.js), plus l'articulation des deux.
**Méthode :** audit grounded sur les failure modes RÉELS reproduits (mesures internes, spot-checks au HEAD courant, tests utilisateurs humains), pas une relecture de code complaisante. Volet front délégué au sous-agent frontend-specialist.

---

## 0. Verdict en une page

OrientAI n'est pas un projet bâclé. C'est un projet sérieux, instrumenté, documenté (28+ ADR, observabilité Langfuse + Ragas, 500+ tests verts, refresh corpus mensuel cron), qui a gagné un concours INRIA sur des critères réels. Le constat "l'IA déçoit" ne vient pas d'un manque de travail mais d'un **désalignement entre ce qui a été optimisé et ce qui fait une bonne expérience d'orientation**.

Le système a été optimisé pour gagner un benchmark qui récompense deux choses : le **sourcing** (citer des sources) et le **refus calibré** (refuser plutôt qu'halluciner). Il gagne sur ces deux axes (92.3 % de refus correct, sourcing supérieur à toutes les baselines). Mais ce benchmark ne mesure NI la fidélité réelle des réponses qu'il donne, NI la satisfaction d'un vrai utilisateur. Or sur ces deux dimensions non mesurées, le système est faible, et c'est vérifié par trois sources indépendantes :

1. **Mesure automatique (Ragas, 2026-05-14)** : faithfulness = 0.489, distribution bimodale. 54 % des réponses extrapolent au-delà des sources, 26 % seulement sont fidèles (≥0.7). Flaggé en interne comme "le bloqueur produit n°1".
2. **Spot-check manuel au HEAD courant (2026-05-13/14)** : sur 13 questions, latences de 20 à 102 secondes, fabrication de programmes inexistants, oscillation entre faux refus et extrapolation.
3. **Tests utilisateurs humains (5 profils, dont un conseiller Psy-EN de 22 ans de métier)** : médiane 2/5, 3 profils sur 5 jugent l'outil "non recommandable pour un mineur en autonomie".

**La tension centrale** (et le coeur de ce qu'il faut résoudre) : le système oscille entre deux défauts opposés. Quand il a de bonnes sources, il extrapole quand même (faithfulness faible). Quand il n'a pas de sources (retrieve raté ou corpus incomplet), il refuse ou invente. Ces deux symptômes ont une **cause amont commune** : la chaîne récupération → génération est faible des deux côtés. La réponse n'est donc PAS un curseur "plus strict / moins strict", mais une refonte de l'amont. C'est l'objet du Livrable 1.

Côté front : le constat de Matteo "les pages ne sont pas au niveau" est partiellement injuste. Le front est techniquement abouti et bien designé. Le vrai problème est que **le front promet (dans le texte et le dossier) plus qu'il ne tient dans le code**, et qu'un point de défaillance unique menace la démo VivaTech.

---

## 1. Audit du coeur IA (OrientIA)

### 1.1 Ce qui est solide (à préserver)

Avant les problèmes, l'inventaire de ce qui marche et ne doit pas être cassé par la refonte :

- **L'intention architecturale est juste** : séparer le savoir (corpus officiel maintenu) de la capacité générative (LLM), refuser plutôt qu'halluciner, tracer chaque chiffre à une source datée. C'est la bonne thèse. Le problème est l'exécution, pas la vision.
- **Le corpus est riche** : 47 214 fiches, 25 sources publiques, refresh mensuel via cron GitHub Actions (`.github/workflows/data-refresh-monthly.yml`). La fraîcheur des données est un avantage structurel réel sur un LLM généraliste au cutoff figé.
- **L'instrumentation est sérieuse** : observabilité Langfuse (10 spans nestés sur `pipeline.answer()`), calibration Ragas, 500+ tests, ADR append-only, dev/test split strict, blinding seed-déterministe, multi-juge. Peu de projets étudiants ont cette rigueur. Cet outillage est exactement ce qui rend la refonte pilotable.
- **Le validator déterministe** attrape programmatiquement certaines hallucinations connues (ECN→EDN, licence ortho inventée) en <1 ms.
- **Quand le retrieve trouve la bonne fiche, le système est bon** : sur le spot-check, Q6 (aides financières), Q8 (emploi cadre Bretagne), Q9 (salaire PCS 37), Q12 (refus honnête bac S) sont des réponses correctes, sourcées, bien calibrées. Le système n'est pas cassé : il est **inconsistant**.

### 1.2 Les failure modes réels reproduits (le POURQUOI de l'insatisfaction)

Je quantifie séparément les deux fils qui tirent dans des directions opposées (recommandation méthodo retenue : ne pas laisser un seul chiffre ancrer l'audit).

#### Fil A - L'IA est trop sèche / refuse à tort / restreint (frustration par pauvreté)

| Symptôme | Preuve | Source |
|---|---|---|
| **Latence rédhibitoire** | Q9 salaire PCS 37 = 102.29 s, Q1 métiers Occitanie = 78.37 s, Q7 Guadeloupe = 57.2 s. Cold-start = 40 s. Le dossier annonce "7-15 s". | `docs/SPOT_CHECK_V5_2026-05-14-post-q11-fix.md` |
| **Faux refus sur donnée existante** | Q10 (insertion bac pro Industrie) : refus "je n'ai pas de données", alors que le corpus contient `inserjeunes_lycee_pro_corpus.json`. Le retrieve a ramené du bruit (doctorat agro, scores 0.68) au lieu de la bonne fiche. | spot-check Q10 + `data/processed/` |
| **Réponses plafonnées à 250 mots** (R6) | Le cap coupe la richesse pour gagner le benchmark. Le dossier lui-même reconnaît que ce cap pénalise "diversité géographique" et "découverte de filières peu connues". | dossier §5.7, `SESSION_HANDOFF.md` §0 |
| **Verrouillage régional** | Restreint les réponses à la région demandée, au prix de la découverte. Pénalité documentée dans le dossier. | dossier §5.7 |
| **Single-turn, aucune mémoire** | Le système répond une question à la fois, ne construit aucun modèle persistant de l'utilisateur. Le scénario "Léo" (campagne de 9 mois) est impossible tel quel. | dossier §5.9 |
| **Template A/B/C infantilisant** | "Plan A/B/C" jugé infantilisant pour un post-terminale par les testeurs. | tests utilisateurs v1/v2 |

#### Fil B - L'IA invente / extrapole (tromperie par excès)

| Symptôme | Preuve | Source |
|---|---|---|
| **Faithfulness 0.489 bimodale** | 54 % des réponses extrapolent (<0.5), 26 % seulement fidèles (≥0.7). Le pipeline produit soit du grounded soit du largement inventé, peu d'entre-deux. | `docs/OBSERVABILITY_SYNTHESIS_2026-05-14.md` |
| **Fabrication de programmes au HEAD courant** | Q11 (BAC PRO agri) : le système invente "Bac pro aménagements paysagers", "Bac pro canin-félin", "Bac pro aquacoles" avec un faux tag "(voir onisep.fr)" et AUCUN [source SX]. Seul 1 des 4 items cités est réellement sourcé. C'est exactement la fabrication que l'architecture prétend empêcher. | spot-check Q11 |
| **Extrapolation depuis fiches non pertinentes** | Q4 (salaire Master Droit PACA), Q13 (insertion doctorat chimie) : retrieve ramène des fiches à score 0.012-0.016 (bruit pur), le LLM brode une réponse à partir de proxies non pertinents. | spot-check Q4, Q13 |
| **Hallucinations survivant aux validators** | ~7 hallucinations distinctes relevées par les testeurs humains : ECN→EDN, bac S cité comme actuel, VAE/VAP impossibles présentées comme possibles, École 42 "gratuite en alternance", coûts privés erronés, formations inventées. | tests utilisateurs v2/v3 |
| **Cause racine documentée** | ADR-037 : "Mistral Medium génération reste fragile, les couches aval compensent mais ne soignent pas à la source." Prompt-engineering seul prouvé insuffisant (ADR-030, preuve empirique : α restricted prompt ne corrige pas les hallucinations). | `SESSION_HANDOFF.md` §15.3, §18.4 |

#### Convergence des deux fils

Les fils A et B ne sont pas contradictoires : ce sont deux sorties d'une même défaillance amont. Quand la récupération est bonne, le générateur extrapole quand même (fil B pur, ex Q5 actuaire qui brode "veille stratégique"). Quand la récupération est mauvaise (scores 0.01-0.02), le système soit refuse (fil A, Q10) soit extrapole depuis le bruit (fil B, Q4/Q13). **La racine est la chaîne retrieve → generation, faible des deux bouts.** La synthèse Langfuse↔Ragas le dit explicitement : "le retrieve a fait un grand pas avec C+, mais la chaîne retrieve → generation a un trou intermédiaire. Le LLM contextualise les bonnes fiches mais extrapole vers une réponse conseiller enrichi."

### 1.3 Problèmes structurels du code (dette technique)

- **Prompt système monstrueux** : `src/prompt/system.py` = 1279 lignes / 72 Ko. Ironie : le dossier lui-même pose la règle R7 "plus la réponse est longue, plus le modèle hallucine" - mais le prompt qui encadre la génération est lui-même énorme, donc fragile, difficile à maintenir, variance-dépendant (ADR-037 note que certaines règles "matchent sur certaines regen Mistral pas d'autres"). Un prompt de 1279 lignes est un symptôme : on a empilé des rustines de couche aval au lieu de soigner la source.
- **Pipeline lourd** : `src/rag/pipeline.py` = 1766 lignes. Accumulation de 11 sprints de patches. Maintenable mais au bord de la complexité ingérable.
- **Prolifération d'index et de corpus** : `data/embeddings/` contient 15+ fichiers `.index` (formations, v5, v6, v7, unified, multi_corpus, dedupe, partition...). `data/processed/` a 20+ variantes de `formations_*.json`. C'est l'archéologie de 2 mois d'itérations rapides, mais le risque d'incohérence index/corpus en prod est réel (quel index est servi par le backend déployé ?).
- **Dépendances observabilité hors manifest** : langfuse, ragas, langchain-mistralai installés mais volontairement absents de `requirements.txt`. Acceptable pour alléger le build prod, mais fragilise la reproductibilité de l'éval.
- **Couches de compensation empilées** : ScopeClassifier + Router + Validator (rules + corpus-check + Layer3 LLM) + post-process. Chaque couche aval a été ajoutée pour compenser une faiblesse du générateur. C'est l'inverse du bon ordre : on devrait soigner le générateur (retrieve + fidélité) avant d'empiler des filets.

### 1.4 Le benchmark est trompeur (et le dossier le reconnaît à demi-mot)

Le benchmark (71 questions, 2 juges LLM) mesure le refus calibré et le sourcing, pas la fidélité ni la satisfaction. Le dossier reconnaît honnêtement deux choses : (a) les juges divergent (Claude favorise OrientAI, GPT-4o favorise Mistral neutre), ce qui signale que "la qualité d'une réponse d'orientation n'est pas une grandeur univoque" ; (b) le système paie un coût mesurable sur la diversité géographique et la découverte. Mais le dossier ne mesure jamais la faithfulness des réponses données, qui est le vrai trou (0.489). **Le benchmark gagné et l'utilisateur déçu ne sont pas contradictoires : ils mesurent des choses différentes.** C'est le constat le plus important de cet audit.

---

## 2. Audit du front (OrientAI_Platform)

Synthèse du sous-agent frontend-specialist (audit grounded sur le code + tests + build, sans screenshots).

### 2.1 Ce qui est solide

Le front est plus abouti que le constat ne le suggère : Next.js 16 + React 19 + shadcn (base-ui) + Tailwind v4, design tokens cohérents et documentés (palette crème / bleu institutionnel / corail, contrastes AAA vérifiés, zéro bleu SaaS générique), streaming SSE correctement câblé (sources puis tokens puis faithfulness puis done, abort propre), 161/162 tests passent, build prod propre. Les 3 modules existent réellement (chat, rendez-vous, calendrier), ce ne sont pas des stubs. Très peu d'"AI slop". Le socle accessibilité est sérieux (skip-link, focus-ring opaque, OpenDyslexic réel, dictée FR, contrastes tokenisés).

**Le problème n'est pas "c'est vide", c'est "ça promet plus que ça ne tient, et le polish surinvesti masque des trous fonctionnels".**

### 2.2 Tableau parité promesse / réalité (extraits les plus graves)

| Promesse (dossier) | Statut | Preuve | Gravité |
|---|---|---|---|
| Assistant IA conversationnel fonctionnel | Partiel | Streaming SSE complet mais dépend de `ORIENTIA_API_URL=localhost:8000` ; backend possiblement non déployé en prod (`route.ts`, `.env`) | **Critique (démo)** |
| Relais déclenché par marqueurs détresse → 3114 / Fil Santé Jeunes | **Absent** | `grep "3114\|Fil Santé\|détresse"` = 0 dans le code applicatif (uniquement texte marketing) | **Critique** |
| Bouton "Prendre RDV" accessible à tout moment dans le chat | Partiel | `/rendez-vous` complet mais aucun CTA inline dans le chat, accessible seulement via sidebar | Élevée |
| Zone conversation `role="log"` aria-atomic (testée NVDA/VoiceOver) | **Livré mais cassé** | `aria-atomic="true"` sur chaque message + live region → re-annonce intégrale à chaque token streamé (bégaiement lecteur d'écran) | Élevée |
| `prefers-reduced-motion` respecté | Partiel | Respecté dans calendrier/booking, PAS dans le chat (Message/Conversation animent en dur) → écart RGAA 13.x sur le module central | Élevée |
| Notifications calibrées par criticité (D-14, D-3) | **Absent** | `reminderWindow` défini dans `timeline.ts` mais lu nulle part ; aucun système de notif | Élevée |
| Score de fidélité affiché à l'utilisateur | Cassé par logique | `FaithfulnessWarning.tsx` n'affiche le score QUE si <0.3 → jamais montré quand la réponse est fiable. On ne montre le score que pour effrayer, jamais pour rassurer | Moyenne |
| Refus honnête → relais conseiller (chemin UI) | Absent | Pas de composant "refus" structuré ni de CTA conseiller au moment du doute | Élevée |
| Mode lecture simplifiée / FALC | Partiel (visuel) | `falcMode` agrandit seulement la typo ; reformulation FALC réelle = "Sprint 14" | Moyenne |
| Scénario Léo bout-en-bout | Partiel | Pas de RDV proposé depuis le chat, pas d'alerte deadline poussée, onboarding sans filière | Élevée |
| Dashboard deadlines centralisées | Livré (affichage) | `timeline.ts` data réelle, tri par criticité ; mais badge "7" hardcodé | Faible |
| Briefing de synthèse édité + consentement explicite | Livré | textarea éditable + aperçu "Transmis au conseiller" | Faible |

### 2.3 Lecture transversale front

Le décalage central n'est pas le design, c'est la **couche "intelligence relationnelle"** promise au dossier : déclenchement détresse, numéros d'urgence, notifications calibrées sont totalement absents du code alors qu'ils sont mis en avant dans le texte. C'est exactement le type d'écart qu'un jury INRIA / AI Act peut sanctionner : le dossier décrit un dispositif de sécurité (détresse → 3114) qui n'existe pas dans le produit. Par ailleurs, l'over-animation du chat (chaque message, chaque source tag en stagger, le faithfulness banner en glow+scale+blur) est à la fois un excès de motion et la cause de l'écart `prefers-reduced-motion`.

---

## 3. Articulation des deux repos + risque infrastructure

### 3.1 Le wiring IA ↔ plateforme

L'architecture cible est : front Next.js (Vercel) → backend OrientIA FastAPI (Railway, `src/api/server.py`, endpoint SSE `/answer/stream`) via un "pont" Pydantic/Zod aligné. Le backend est **déployable** : Dockerfile Railway-ready (`uvicorn src.api.server:app` sur `$PORT`), `.railwayignore` dédié pour embarquer le corpus (gitignored mais nécessaire au runtime), et l'historique git montre un "post backend Railway fix" (#33). Le streaming, l'AbortController et le bouton Stop ont été câblés.

### 3.2 Le risque numéro un VivaTech (à vérifier immédiatement)

Le `.env` du repo plateforme pointe `ORIENTIA_API_URL` vers `localhost:8000`. La valeur de prod est une variable d'environnement Vercel (hors repo, non vérifiable depuis le code). **Question ouverte critique : en prod, cette variable pointe-t-elle vers une instance Railway live et joignable, ou est-elle restée sur localhost / non configurée ?** Si le backend n'est pas joignable depuis le domaine de prod, le chat renvoie 503 et le coeur de la démo (l'IA) est mort sur scène.

Le probe live (2026-06-08) renvoie HTTP 429 (firewall Vercel / rate-limit / onboarding-gate), ce qui n'a pas permis de confirmer le backend de bout en bout sans risquer de déclencher l'Attack Mode. **Action P0 avant le 16/06 : Matteo ou Jarvis vérifie dans le dashboard Vercel que `ORIENTIA_API_URL` prod pointe vers le Railway live, et teste une vraie question sur https://orientai-platform.fr.** C'est le point de défaillance unique de la démo.

### 3.3 Autres risques démo (frontend-specialist)

- **Cold-start 40 s sans loader progressif** = 40 s de silence sur scène. Prévoir une question pré-chauffée + un loader qui rassure.
- **Lecteur d'écran** : si un évaluateur teste l'accessibilité (argument central revendiqué), le bégaiement aria-atomic est immédiatement audible et décrédibilise la promesse RGAA.
- **Mode FALC** : un évaluateur qui l'active ne verra qu'un agrandissement de typo (reformulation réelle = Sprint 14).
- **Question "où est le relais détresse / le bouton conseiller dans le chat"** : pas de réponse produit aujourd'hui.

---

## 4. Synthèse de l'audit : la hiérarchie des causes

Du plus profond au plus superficiel :

1. **Cause racine (générateur + récupération)** : Mistral Medium extrapole au lieu de citer (faithfulness 0.489), et le retrieve rate les questions indirectes / hors couverture (scores bruit 0.01-0.02). Tout le reste découle de là. → adressé par Livrable 1, chantier de fond.
2. **Conséquence directe** : oscillation faux refus / hallucination, empilement de couches de compensation (prompt 1279 lignes, validators multiples).
3. **Couverture corpus incomplète** : agriculture, DOM-TOM, reconversion adulte, privé hors RNCP → faux refus structurels.
4. **UX restrictive** : cap 250 mots, verrouillage régional, single-turn, template A/B/C → frustration même quand la réponse est correcte.
5. **Latence** : 20-100 s → abandon avant même de juger la qualité.
6. **Front : écart promesse/réalité** : relais détresse absent, notifications déclaratives, score de fidélité caché en cas de succès, a11y cassée sur le module central.
7. **Risque infra** : wiring backend prod non confirmé (P0 démo).
8. **Benchmark inadéquat** : mesure le refus, pas la fidélité ni la satisfaction → on pilotait sur le mauvais indicateur.

Le détail de l'écart vers la cible idéale et le séquencement (quick wins vs chantier de fond, axe VivaTech) sont dans le Livrable 3.

---

*Sources principales : dossier 44p (`_orientai-ref/`), `OrientIA/docs/OBSERVABILITY_SYNTHESIS_2026-05-14.md`, `OrientIA/docs/SPOT_CHECK_V5_2026-05-14-post-q11-fix.md`, `OrientIA/docs/SESSION_HANDOFF.md` §14-18, `OrientIA/CLAUDE.md`, tests utilisateurs `OrientIA/results/user_test*`, audit frontend-specialist du repo `OrientAI_Platform`.*
