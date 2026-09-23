# STATE - Set de pertinence lot 2.1 (checkpoint pre-clear 16/07 ~19h)

Ordre : 2026-07-16-0905, lot 2, sous-chantier 1. Branche : feat/h1-lot2-relevance-set.

## Fait (committe ici)

- mine_candidates.py : mining TRI-MODAL (dense FAISS top-20 + BM25 top-20 +
  lexical deterministe top-15, anti-biais retrieval) sur les 387 questions
  retrieval-pertinentes du banc 497q + 3 questions MIAGE. EXECUTE :
  candidates.json = 387 questions, 9 092 candidats (median 21/q).
- batches/ : 26 lots de ~15 questions pour la flotte de juges.
- src/eval/relevance_metrics.py + tests/test_relevance_metrics.py (11 verts) :
  recall@k (grade 2 uniquement, none_relevant hors denominateur) + nDCG@k
  (gains gradues, None si pas de verite terrain - jamais de 0 fabrique).
- eval_retrieval.py : runner 2 modes (--mode raw = retrieve+rerank+MMR sans
  LLM, gate CI gratuit ; --mode serving = _prepare_for_generation complet,
  ~2 appels small/question, pour les baselines de lot).
- labels_partial.json : 135/387 questions labellisees (9 lots de juges sur 26,
  coupure quota session 16/07 18h40).

## A REPRENDRE (dans l'ordre)

1. BUG MINER a corriger AVANT de relancer les juges : fiche_id "idx:-1"
   (382/9092 candidats, 79 refs dans les labels partiels). Cause :
   mine_candidates.py branche dense, ligne `fid = _fiche_id(fiche,
   index_by_fid.get(...))` - fallback foireux quand la fiche n'a pas de champ
   `id`. Fix : construire index_by_id une fois (id(fiche_objet) -> index
   corpus) ou porter l'index de position dans le retour de retrieve_top_k.
   Puis RE-MINER (le mining est resume-safe : supprimer candidates.json
   d'abord), re-decouper les batches, et INVALIDER les labels idx:-1
   (les 135 questions restent valides SAUF leurs refs idx:-1 a rejuger).
2. Relancer la flotte : Workflow resumeFromRunId "wf_1e24eb24-ae3", script :
   /home/matteo_linux/.claude/projects/-home-matteo-linux-projets-OrientIA/e71761f5-59e4-4fb9-920a-98b0681c0eee/workflows/scripts/label-relevance-set-wf_1e24eb24-ae3.js
   ATTENTION : si les batches changent (fix idx:-1), le cache tombe - relancer
   un run NEUF plutot, et fusionner avec labels_partial.json (135 qids deja
   juges, purger leurs refs idx:-1).
3. Assembler labels.json complet -> baseline : eval_retrieval.py --mode raw
   (gratuit) puis --mode serving (~0.5 EUR small). Pinger la baseline
   recall@5/nDCG@10 a Jarvis (il l'attend explicitement).
4. Gate CI : test type golden (skip si index absent) + brancher dans
   .github/workflows (pattern golden-ci existant).

## Extension de scope lot 2 (Jarvis 16/07 ~19h20, au vault aussi)

(a) donnees COUTS DE SCOLARITE (frais universites vs ecoles privees) ;
(b) fiches CONCEPT generiques (BUT vs BTS, PASS/LAS, alternance mode d'emploi)
    - les questions generiques recoivent des reponses par instances ;
(c) GEO = priorite 1 du retrieval (recit Nantes a compare Draguignan et Paris,
    verdict INFIDELE - LE rate de la session utilisateur de Jarvis).
Ces 3 items s'ajoutent au scope existant (ADR-058 re-embed, routing salaire
MIAGE, multi-tour standalone-rewrite, reranker domain/domaine + cross-encoder).

## Observations utiles pour la suite du lot 2 (des labels partiels)

- Beaucoup de none_relevant/grade-1-seulement sur les factuelles precises :
  les stats fines (salaire median par formation-ville, insertion a 6 mois par
  ville) n'existent souvent PAS dans le corpus au grain demande -> une part
  des refus est de la DATA manquante, pas du retrieval rate (confirme
  l'extension de scope data ci-dessus).
- Le juge de fact-001 confirme le finding live : "BUT Informatique a Lyon"
  -> dense#1 = Martinique, aucun BUT Info lyonnais dans les candidats.
