# Set de pertinence : état au 23/09/2026

Mesure le retrieval contre des fiches jugées pertinentes, question par question. Commencé le 16/07 (ordre
2026-07-16-0905, lot 2.1, commit WIP `c7402d3`), repris dans le lot 0 du 23/09 (ordre 2026-09-23-0817).

## Ce qui est en place

- `mine_candidates.py` : candidats tri-modaux (dense top-20, BM25 top-20, lexical top-15) pour les 387 questions
  retrieval-pertinentes du banc 497q, plus 3 questions MIAGE. Re-miné le 23/09 après correctif :
  16 939 candidats (médiane 44 par question), contre 9 092 avant (médiane 21).
- `labels_partial.json` : 135 questions sur 387 labellisées le 16/07 par une flotte de juges (9 lots sur 26),
  migrées le 23/09 vers la clé `idx:<position>` par `migrate_labels_idx.py`. Les 1 172 références sont résolues,
  0 perdue. 86 questions sont scorables (au moins une fiche de grade 2), 6 sont `none_relevant`.
- `eval_retrieval.py` : `--mode raw` (retrieve, rerank, MMR, sans LLM) et `--mode serving` (ce que le LLM voit),
  recall@5, recall@10 et nDCG@10 (`src/eval/relevance_metrics.py`).

## Le bug corrigé le 23/09

Le miner identifiait une fiche par son champ `id`, absent sur 38 596 des 52 040 fiches, et les modes dense et
BM25 rendaient alors `idx:-1` : 382 candidats confondus en un seul par question. `eval_retrieval.py` lisait
lui aussi `id` : les fiches sans `id` sortaient du classement. Sur le run raw du 23/09, l'ancienne clé rendait un recall@10
de 0,198 au lieu de 0,419. La clé est désormais la position dans `formations.json`, retrouvée par identité
d'objet et épinglée par le sha256 du corpus (`src/eval/battery/corpus.py`).

## Mesures du 23/09 (corpus `2e4276e6155b`, 86 questions scorables)

| mode | recall@5 | recall@10 | nDCG@10 | trace |
|---|---|---|---|---|
| raw | 0,314 | 0,419 | 0,142 | `results/relevance/2026-09-23_raw.json` |
| serving | 0,547 | 0,616 | 0,262 | `results/relevance/2026-09-23_serving.json` |

En serving, 15 questions sur 135 ne servent aucune fiche (court-circuit scope ou routeur) : elles comptent
comme des échecs quand elles sont scorables.

**Ce sont des bornes basses.** Le pool jugé le 16/07 avait perdu les candidats confondus en `idx:-1`. Pour les
135 questions labellisées, 49 % (médiane) du pool re-miné n'a jamais été jugé : une fiche pertinente de cette
moitié, si le retrieval la trouve, compte comme un échec.

## À reprendre

1. Rejuger les 135 questions sur le pool re-miné (la moitié non jugée), puis labelliser les 252 restantes.
   Les lots de juges (`batches/` du WIP) ne sont pas repris : ils découpaient l'ancien pool.
2. Brancher le recall en gate CI (skippé si l'index est absent), sur le modèle de golden-ci.

`golden_qa` (676 questions) ne porte aucune vérité terrain de pertinence (question et réponse seulement, aucun
identifiant de fiche) : on ne peut pas y mesurer de recall.
