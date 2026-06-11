# L2 - Harnais d'évaluation reproductible

Ordre : 2026-06-09-1030-claudette-orientai-audit-empirique
Auteur : Claudette
Date : 2026-06-09
Objet : un harnais re-exécutable qui mesure fidélité (groundedness) ET retrieval, sur un eval set versionné, pour sortir des impressions et re-mesurer après chaque changement.

---

## 1. Ce qui est livré (et qui tourne)

| Composant | Script | Mesure | Statut |
|---|---|---|---|
| Runner pipeline réel | `run_battery.py` | sorties brutes + scope + sources + validation + latence | OPÉRATIONNEL (42 q) |
| Juge de groundedness | `judge_groundedness.py` | fidélité claim par claim, taxonomie d'échec | OPÉRATIONNEL (42 q jugées) |
| Audit data | `data_audit.py` | couverture/null/fraîcheur du corpus | OPÉRATIONNEL |
| Stabilité scope | `scope_stability.py` | (non-)déterminisme du classifieur, 6 runs | OPÉRATIONNEL |
| Recall retrieval | `recall_probe.py` | recall@k BM25 sur cibles nommées | OPÉRATIONNEL |
| Eval set versionné | `eval_set.json` | 42 sondes par catégorie de risque | VERSIONNÉ |

Toutes les sorties brutes sont dans `results/`, vérifiables une par une.

Propriétés : resume-safe (écriture incrémentale, reprise sur les ids non faits), eval set versionné (comparaisons avant/après valides), séparation observation/jugement (on capture le brut, on juge ensuite, on peut re-juger sans re-générer), juge d'une autre famille que le générateur (Claude juge, Mistral génère - pas d'auto-jugement).

---

## 2. Métrique de fidélité (groundedness)

Le juge décompose chaque réponse en claims atomiques et vérifie, claim par claim, si chaque affirmation factuelle est SUPPORTÉE par les sources réellement fournies au générateur (pas par la connaissance du monde du juge). Il classe aussi l'outcome (grounded / unsupported / metric_substitution / honest_refusal / off_topic / crisis).

Résultats run v2 (42 questions) :
- Groundedness moyenne sur les réponses qui affirment quelque chose (n=17) : **0,766**.
- Hallucination de chiffres : **2/42**.
- Substitution de métrique : **4-5/42**.
- Écarts honesty_score interne vs juge externe (self >= 0,9, juge < 0,7) : **4**.

Pourquoi un juge custom plutôt que Ragas : Ragas est câblé dans le repo (`scripts/observability/run_ragas_calibration.py`) mais (a) son intégration dépend d'un shim mistralai fragile, (b) il rend un score moyen opaque (le repo a lui-même mesuré 0,489 sur un golden set dont il a dû déclarer `context_recall` inutilisable, artefact de protocole), (c) il juge avec le même fournisseur que le générateur. Un juge LLM custom, claim par claim, d'une autre famille, est plus transparent (chaque verdict est inspectable), plus robuste (pas de dépendance shim), et c'est le coeur de la méthode L4. Ragas reste disponible en cross-check ; il n'est pas la source de vérité.

Note de comparaison honnête : la Ragas 0,489 du repo et ma groundedness 0,766 ne se contredisent pas vraiment - grains différents, échantillons différents, et ma mesure exclut les refus purs (qui n'affirment rien). Aucune des deux n'est "la vérité" seule. Le point qui compte, robuste aux deux mesures : le mode d'échec dominant est le calibrage/la pertinence, pas l'effondrement de la fidélité.

---

## 3. Métrique de retrieval (recall)

`recall_probe.py` mesure, pour des questions ciblant une formation nommée, si la cible apparaît dans le top-k retrieval (proxy lexical BM25, déterministe, sans API).

Résultat : **BM25 recall@30 = 5/8** sur cibles nommées.
- Trouvées : BUT Info IUT Lyon 1 (rang 1), licence droit Dauphine (rang 1), INSA Lyon (rang 1), licence psycho (rang 1), prépa MPSI lycée du Parc (rang 4).
- Manquées : BUT Info IUT Bourges, BTS SIO SLAM, BUT TC IUT Annecy.

Lecture croisée avec L1 : le BUT Info Lyon 1 est trouvé au rang 1 mais REFUSÉ par le pipeline (sur-refus en aval, pas un problème de retrieval). Les 3 manques (BTS, IUT spécifiques) sont des trous de couverture/index réels (cohérent avec L3 : BTS et certaines voies mal couverts). Le recall n'est donc pas le seul coupable : il y a un problème de retrieval ET un problème de gating en aval qui jette des cibles pourtant trouvées.

Limite assumée : c'est un proxy lexical sur 8 cibles, pas un recall@k complet sur un set de pertinence labellisé. Le harnais complet (set labellisé question -> fiche(s) pertinente(s), recall@5/MRR/nDCG, dense+lexical) est le prochain incrément - la base (`recall_probe.py`) est en place pour l'étendre.

---

## 4. Comment re-mesurer après un changement

```bash
cd ~/projets/OrientIA && source .venv/bin/activate
# 1. re-générer les sorties sur le MEME eval set
PYTHONPATH=. python audit_empirique_2026-06-09/run_battery.py \
    --eval-set audit_empirique_2026-06-09/eval_set.json \
    --out audit_empirique_2026-06-09/results/battery_run_v3.json
# 2. re-juger
PYTHONPATH=. python audit_empirique_2026-06-09/judge_groundedness.py \
    --in  audit_empirique_2026-06-09/results/battery_run_v3.json \
    --out audit_empirique_2026-06-09/results/groundedness_v3.json
# 3. diff v2 vs v3 (groundedness, outcomes, hallu, substitution)
```

Cibles de production proposées (gating) : groundedness >= 0,90 sur les réponses affirmatives, 0 hallucination de date/chiffre, substitution de métrique = 0, faux positif urgent = 0 sur les sondes de précision, recall@5 >= 0,85. Aucune mise en prod sans passage des seuils.

---

## 5. Limites du harnais (honnêteté méthodo)

- Le juge est un seul LLM (Claude Sonnet) : idéalement 2 juges + accord inter-juges. Mono-juge = un seul biais.
- L'eval set fait 42 questions : suffisant pour un diagnostic qualitatif des modes d'échec, insuffisant pour une significativité statistique (le dossier lui-même vise plusieurs centaines de questions). À étendre, en y versant chaque échec réel observé.
- Recall = proxy BM25 sur 8 cibles, pas un set labellisé complet.
- Scope non déterministe : toute métrique sur le scope doit être moyennée sur N runs (cf `scope_stability.py`), pas mesurée une fois.

Ces limites sont le périmètre du prochain incrément, pas des trous cachés : le harnais actuel suffit à mesurer un avant/après sur les modes d'échec identifiés, ce qui est l'usage immédiat.
