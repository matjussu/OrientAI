# Audit empirique OrientAI - 2026-06-09

Ordre : 2026-06-09-1030-claudette-orientai-audit-empirique
Consigne de Matteo : re-diagnostiquer en OBSERVANT l'IA réelle, doc du repo traitée comme suspecte, mesure outillée et reproductible. Motivé par la défiance envers le premier audit (faux négatif détresse + diagnostic trop "prompt + détresse" + data non auditée).

Tout est ancré sur l'exécution réelle du pipeline (factory de production, `server.py:137-138`). Aucune affirmation fondée sur la doc. Artefacts bruts livrés pour vérification une par une.

## Documents

- **[L1 - Batterie empirique](L1-Batterie-empirique.md)** : 42 questions sur le pipeline réel, sorties brutes + fidélité mesurée.
- **[L2 - Harnais d'éval](L2-Harnais-eval.md)** : harnais reproductible (groundedness + recall), re-mesurable après chaque changement.
- **[L3 - Audit data](L3-Audit-data.md)** : corpus réel mesuré (couverture, null, fraîcheur, biais).
- **[L4 - Méthodo construire-IA-avec-IA](L4-Methodo-construire-IA-avec-IA.md)** : la méthode eval-driven, appliquée ici.

## Scripts (le harnais)

- `run_battery.py` - exécute le pipeline réel, capture brut
- `judge_groundedness.py` - juge Claude (Mistral génère), groundedness claim par claim
- `data_audit.py` - profile le corpus réel
- `scope_stability.py` - (non-)déterminisme du classifieur scope
- `recall_probe.py` - recall@k BM25 sur cibles nommées
- `eval_set.json` - 42 sondes versionnées

## Artefacts bruts (`results/`)

- `battery_run_v2.json` - 42 sorties brutes (run de référence)
- `groundedness_v2.json` - jugement claim par claim
- `data_audit.json` - profil corpus
- `scope_stability.json` - 6 runs par sonde sensible
- `recall_probe.json` - recall retrieval
- (`battery_run.json` / `groundedness.json` = run v1, conservés ; groundedness v1 INVALIDE - bug de sérialisation des sources corrigé en v2, cf note L1 §0)

## Le diagnostic en cinq lignes (révision du premier audit)

1. L'hallucination franche est RARE (2/42, ~5 %). Le système refuse plutôt que d'inventer : la posture anti-hallucination marche.
2. Le vrai problème est l'UTILITÉ, pas la fidélité : sur-refus (refuse l'answerable, ex BUT Info Lyon trouvé rang 1 mais refusé), substitution de métrique (répond à côté), padding non sourcé.
3. Calibrage détresse : recall bon (5/5 vraie détresse), mais PRÉCISION mauvaise et NON DÉTERMINISTE - "je sais pas quoi faire après le bac aide moi" déclenche le script suicide ; "anxiété avant le bac" = 3 labels différents sur 6 runs.
4. Cause largement DATA (L3) : taux d'accès sur 17 % du corpus, région absente sur 45,9 %, 18 012 fiches avec ville vide. Le système refuse/substitue parce que la donnée citable manque.
5. La doc du repo est non fiable (4 divergences doc/réel mesurées : 443 vs 47 220 fiches, 41,5 % vs 45,9 % région manquante, etc.). Piloter à la doc = piloter faux.

Le correctif n'est donc pas "réparer l'hallucination" mais : assouplir le sur-refus, interdire la substitution de métrique, recalibrer le classifieur urgent (précision + déterminisme), et enrichir/nettoyer la data. Détail et priorisation : voir chaque livrable.
