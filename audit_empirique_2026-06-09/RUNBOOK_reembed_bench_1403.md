# Runbook — Re-embed + bench e2e (ordre 2026-06-14-1403)

Auteur : Claudette · Date : 2026-06-14 · État : PRÉPARÉ (free gate passé), spend+bench À EXÉCUTER.

> Recommandation : exécuter le spend + bench en session FRAÎCHE (contexte propre pour
> l'opération coûteuse et précision-critique qui gate la prod VivaTech — discipline
> [[feedback-context-saturation-handoff]]). Toute la prep de-risque est faite ci-dessous.

---

## État PRÊT (vérifié cette session)

- **Corpus filé + vérifié** : `data/processed/formations.json` (52040) contient le set
  prouvé : type_diplome global 35316 (dont rncp Titre pro 2224), lycée_pro insertion_pro
  2542, onisep niveau 3614, ROME passerelles/RIASEC 1584, region Polynésie ~90.
  48032 fiches retrieval_eligible (à embedder).
- **Ancien index sauvegardé** (= AVANT, pour le côte-à-côte) :
  `data/embeddings/formations.index.before-fills-20260614` (213 Mo).
- **Free gate** : clé Mistral OK, coût réel estimé **~$0.74** (7.4M tokens à 0.1$/M ;
  la figure "$5-10" du projet est conservatrice).
- **Garde-fou ADR-033 vérifié** : ROME hors du dense (fiche_to_text identique avant/après
  sur les 1584 métier) -> les passerelles n'apparaissent qu'en fact_card/génération.

## Runbook spend (le ré-embed est Matteo-gated — déclencher via `!` ou go explicite)

```bash
cd ~/projets/OrientIA && source .venv/bin/activate
# 1) Re-embed formations.json -> formations.index  (LE script correct, PAS embed_unified.py
#    qui cible formations_unified.json = mauvais corpus). ~$0.74, ~20-40 min (rate-limit Mistral).
PYTHONPATH=. python scripts/rebuild_faiss_index.py
# 2) Re-partitionner en quad sub-indexes + manifest (gratuit, local) — la prod lit le manifest.
PYTHONPATH=. python scripts/build_quad_subindexes.py
```
Pièges : CLAUDE.md dit `python -m src.rag.embeddings` = STALE (n'existe pas).
`embed_unified.py` = mauvais corpus (unified). Le bon = `rebuild_faiss_index.py`.

## Bench e2e (après re-embed) — comparaison ANCIEN vs NOUVEAU index

- ANCIEN index = `formations.index.before-fills-20260614` ; NOUVEAU = `formations.index` (rebuild).
- L'apply (scripts/apply_derive_fields_phase1a.py) part du backup corpus + fills SEULEMENT
  -> le delta avant/après est ISOLÉ aux fills (pas d'autre changement). Bon pour le bench.
- **~20-30 Q curées** (réponses MODÈLE côte-à-côte, pas juste retrieval) :
  - typage : "BUT info ou prépa MPSI ?", "comparer BUT vs école d'ingé", "BTS vs BUT compta"
  - titres pros RNCP : "c'est quoi un titre professionnel RNCP ?", "certification pro pour devenir X"
  - emploi lycée pro : "taux d'emploi après bac pro commerce", "débouchés bac pro"
  - passerelles ROME : "vers quoi évoluer après bûcheron / boulanger ?", "reconversion paysagiste"
- **golden 50q** : non-régression (faithfulness/retrieval) — PAS les 497q (consigne Matteo).
- Rapport : exemples CONCRETS avant/après pour Matteo + verdict régression.

## Gotchas bench

- Garder l'ancien index (fait). Ne PAS écraser le backup.
- ROME passerelles = fact_card only -> visibles dans les RÉPONSES (génération), pas dans
  le retrieval. Les probes passerelles testent la génération, pas le rang retrieval.
- Le re-embed consolide en dense : type_diplome (parcoursup/monmaster/rncp), region, onisep
  niveau (champs de fiche_to_text). lycée_pro insertion (annex) et ROME = PAS dans le dense
  (servis en fact_card) -> leur gain se voit en génération, pas en retrieval.
- Coût génération bench : ~20-30 Q × 2 index + golden 50q = budget génération à prévoir
  (Mistral medium), distinct du re-embed.
