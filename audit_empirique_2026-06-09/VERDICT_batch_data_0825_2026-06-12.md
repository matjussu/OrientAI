# Verdict PR data — ordre 0825 (batch data pré-reembed) — 2026-06-12

PR data = Phase 0 (canary) + Phase 1 (quartiles). Phase 2 classée déjà livrée.
Phase 3 (re-embed + re-run 497q) et Phase 4 (CI golden 50q) sont hors de cette PR.

## Phase 0 — Canary juge groundedness : PASS

Avant le re-embed qui re-gèle la baseline, on a vérifié que le juge actuel
(claude-haiku-4-5-20251001) reproduit le gel sur 30 réponses figées (stratifié par
outcome, 10 cas hallucinated_numbers inclus de force). Outcome 30/30 = 100% (gate
>=95%). Jitter groundedness 0.03 + 3 flips hallu = bruit temp=0, zéro drift
systématique. Détail : `VERDICT_canary_juge_2026-06-12.md` + `canary_2026-06-12/`.

**Caveat re-gel (Phase 3)** : le flag hallucinated_numbers a ~10% de jitter
par-question sur les cas-limites de mauvais-usage de nombre. Le compteur hallu
(10/497) peut bouger de +/-2-3 au re-run par pur bruit de juge. Signal fiable =
outcome bucket + magnitude, pas le +/-2-3.

## Phase 1 — Fourchette salaire Q1/Q3 InserSup

Ajout des quartiles Q1/Q3 (net, MÊME horizon que la médiane retenue : 12m prioritaire
sinon 30m — jamais de mélange) en complément de la médiane C2b.

- `insersup_salary.py` : parse Q1/Q3 par horizon ; attach pose la fourchette ; mode
  BACKFILL pour compléter les quartiles sur le corpus servi déjà médiane-enrichi C2b,
  SANS re-toucher la médiane, UNIQUEMENT si la médiane vient d'InserSup (garde anti
  cross-source).
- `_salary_fragment` (embed, retrievable) + `FactChiffres` (générateur cite la
  fourchette) ; `_FICHE_KEEP` garde `insertion_pro` entier -> juge voit la fourchette
  (vérifié).
- Migration appliquée au corpus servi (backup) : **3854/3854 médianes InserSup ont la
  fourchette, 0 violation Q1<=médiane<=Q3**. 201 doctorats restent médiane-seule (l'IP
  Doc n'a pas de quartiles : pas de fabrication).
- Sans re-embed (index figé, fact_card lit live). Les quartiles entrent au retrieval au
  re-embed Phase 3.
- Tests : 17 insersup_salary (backfill + garde cross-source + horizon + idempotence) +
  fourchette fact_card/embeddings. Suite complète VERTE (2965 passed).

Résidu (hors scope, non touché) : 76 ambiguïtés InserSup (même clé+promo, salaires
divergents), déjà présentes C2b.

## Phase 2 — Calendrier Parcoursup : DÉJÀ LIVRÉE (08/05)

Vérifié avant tout code (réflexe vérifier-avant-réimplémenter) : le calendrier demandé
existe déjà. Builder `build_calendrier_corpus.py` (08/05, dates .gouv.fr vérifiées),
intégré via `run_merge_v3.py` (committés), 21 fiches domain=calendrier (9 Parcoursup +
7 MonMaster + 5 DSE) retrieval_eligible, surface au générateur (fact_card.text_libre) +
juge (`_FICHE_KEEP` via `text`). Anti-fabrication de date déjà fonctionnelle et
déterministe (sonde temp=0 : 2027 et 2025 hors-corpus -> disclaimer, ZÉRO date inventée ;
2026 -> 1er avril 2026 sourcé). Aucun garde déterministe ajouté (risquerait de régresser
le comportement disclaim+offre-2026 idéal). Origine de l'ordre : ligne "AUCUNE source
calendrier" de la queue 22q, factuellement périmée (corpus pas re-vérifié au scoping).

### Reclassement fact-025-v1 (pour lecture du re-gel de ce soir)

Les 4 variantes fact-025 ont reçu au gel 10/10 sources domaine calendrier (la queue
était fausse sur l'absence de sources). Scores gel :

| variante | question (paraphrase) | outcome | groundedness |
|---|---|---|---|
| fact-025 | "Quelle est la date limite... 2025 ?" | answered_alternative_disclaimed | 1.0 |
| fact-025-v1 | "Dis-moi : Quelle est la date limite... 2025 ?" | answered_unsupported | 0.0 |
| fact-025-v2 | "J'aimerais savoir, quelle est... 2025 ?" | answered_alternative_disclaimed | 1.0 |
| fact-025-v3 | "Peux-tu m'aider : quelle est... 2025 ?" | answered_grounded | 1.0 |

Même question, mêmes sources, 3 paraphrases au comportement idéal et 1 ratée : le résidu
v1 (0.0) est de la **variance de génération sous paraphrase**, ni data ni retrieval. Il
rejoint le bucket sur-élaboration 14/22 (constrained decoding, post-VivaTech). Un garde
déterministe rattraperait v1 au prix d'un risque de régression sur les 3 variantes
idéales : non rentable. Si v1 flappe au re-gel de ce soir, le lire comme variance
attendue, pas comme régression calendrier.
