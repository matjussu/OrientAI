# L4 - Construire une IA avec une IA (méthodologie eval-driven)

Ordre : 2026-06-09-1030-claudette-orientai-audit-empirique
Auteur : Claudette
Date : 2026-06-09
Objet : formaliser la méthode de développement assisté par IA appliquée à OrientAI, et la rendre rigoureuse. Cette méthode n'est pas théorique : elle est exactement celle utilisée pour produire L1, L2 et L3 du présent audit. Les scripts cités existent dans `audit_empirique_2026-06-09/`.

---

## 0. Pourquoi ce volet

Le projet OrientAI est lui-même construit avec une IA (Claude/Claudette code le pipeline). Le premier audit a échoué sur un point (faux négatif détresse) précisément parce qu'il a lu du code et de la doc au lieu d'observer le comportement réel. La leçon est méthodologique avant d'être technique : **quand on construit une IA avec une IA, la boucle qui compte n'est pas écrire-du-code, c'est observer-mesurer-corriger sur le système réel.** Ce document décrit cette boucle et comment l'outiller.

Principe directeur, valable pour l'audit comme pour le futur dev : **aucune affirmation sans observation, aucune métrique sans mesure reproductible, aucun juge qui se juge lui-même.**

---

## 1. Les quatre piliers

### Pilier 1 - Observer le système réel, pas sa représentation

Le code dit ce que le système est censé faire. La doc dit ce qu'il faisait à un instant T (et vieillit mal : la doc d'OrientIA annonçait 443 fiches, le corpus réel en compte 47 220 ; elle annonçait 41,5 % de région manquante, la mesure réelle donne 45,9 %). Seule l'exécution dit ce qu'il fait vraiment.

Application concrète : `run_battery.py` construit le pipeline via la factory de production (`make_production_pipeline`, identique à `server.py:137-138`) et capture la sortie BRUTE de chaque question, plus le scope, la validation auto-déclarée, les sources, la latence. On ne résume pas : on archive le brut, vérifiable un par un.

### Pilier 2 - Le juge est une autre IA, jamais le générateur

Le `honesty_score` interne d'OrientIA était faussement confiant (~0.95 affiché, hallucinations réelles derrière) parce que le système se jugeait lui-même. Règle : **le juge de groundedness appartient à une autre famille de modèle que le générateur.** Ici générateur = Mistral Medium, juge = Claude Sonnet (`judge_groundedness.py`). Le juge reçoit la question, la réponse, et les sources EXACTES fournies au générateur, puis vérifie claim par claim si chaque affirmation factuelle (surtout les chiffres) est supportée par ces sources, pas par sa connaissance du monde.

### Pilier 3 - Mesurer au bon grain : la phrase, pas la moyenne

Une faithfulness moyenne de 0.8 masque qu'une réponse sur cinq invente. L'état de l'art 2026 le confirme : la groundedness phrase par phrase (fraction de phrases ancrées) détecte ce que la moyenne cache, et désigne la phrase exacte à corriger. Le juge décompose donc en claims atomiques et rend un verdict par claim, pas un score global opaque.

### Pilier 4 - Distinguer les modes d'échec, ne pas tout appeler "hallucination"

Un audit utile ne dit pas "l'IA est mauvaise", il dit POURQUOI et OU. La taxonomie d'échec utilisée :
- `answered_grounded` : répond, tout sourcé. (l'objectif)
- `answered_unsupported` : répond mais au moins un claim non supporté. (hallucination franche)
- `metric_substitution` : refuse/n'a pas la métrique demandée mais en sert une autre comme si pertinent (ex : insertion demandée -> taux d'accès Parcoursup d'autres formations). (pertinence)
- `honest_refusal` : refuse proprement, n'invente rien. (bon comportement, sauf si la donnée existait -> over-refusal)
- `off_topic` : répond à côté sans le signaler.
- court-circuits : `crisis_response` (détresse), `shortcircuit_out_of_scope`.

Distinguer hallucination, substitution et sur/sous-refus change le diagnostic : on ne corrige pas un problème de calibrage comme un problème de génération.

---

## 2. La boucle build-eval-iterate (outillée)

```
   [eval set versionné]            <- jeux de questions + sondes adversariales (eval_set.json)
            |
            v
   [run sur pipeline réel]         <- run_battery.py : sorties brutes + scope + sources + latence
            |
            v
   [mesure multi-juge]             <- judge_groundedness.py (Claude juge) : groundedness claim-par-claim
   [+ data audit]                  <- data_audit.py : couverture, null, fraîcheur, biais d'indexation
            |
            v
   [diagnostic par mode d'échec]   <- taxonomie : hallu / substitution / over-refusal / calibrage
            |
            v
   [changement ciblé]  -----------> retour en haut : on re-run le MEME eval set, on diff avant/après
```

Propriétés non négociables de la boucle :
- **Eval set versionné** : on mesure toujours sur le même jeu, sinon les comparaisons avant/après ne valent rien.
- **Resume-safe et incrémental** : chaque script écrit après chaque item, reprend où il s'est arrêté (run interrompu = pas de perte, pas de double-coût API).
- **Artefacts bruts conservés** : les sorties réelles sont archivées pour audit externe (Jarvis vérifie une par une, pas le résumé).
- **Séparation observation / jugement** : on capture d'abord le brut (run_battery), on juge ensuite (judge_groundedness). On ne mélange pas, pour pouvoir re-juger sans re-générer.

---

## 3. Génération de jeux adversariaux assistée

Plutôt que d'écrire à la main un eval set qui reflète nos propres angles morts, on génère des sondes adversariales par catégorie de risque connue :
- factuelles précises propices à l'invention (taux, salaires, dates d'une formation nommée),
- pièges de couverture (DOM-TOM, agricole, région manquante - ciblés sur les trous mesurés en L3),
- détresse explicite ET implicite, plus des sondes de PRECISION (faux positifs : "anxiété avant le bac" doit-il déclencher la crise ?),
- substitution de métrique (demander l'insertion d'une formation dont seul le taux d'accès existe),
- injections de prompt et superlatifs/pronostics interdits.

Le bon réflexe "IA qui construit une IA" : quand un cas réel échoue (remonté par un test live, ou par un utilisateur), il devient immédiatement une entrée du eval set versionné. Le set grandit avec les échecs observés ; il ne reste jamais figé sur l'intuition initiale.

---

## 4. Garde-fous de la méthode (les pièges du dev assisté par IA)

1. **Ne jamais croire un score auto-déclaré par le système audité.** (cf honesty_score 0.95 faussement confiant.)
2. **Ne jamais généraliser un grep scopé en claim système.** (cf faux négatif détresse : grep du seul front -> "absent du code" alors que la fonction est dans le backend.) Vérifier sur tous les périmètres.
3. **Traiter la doc comme une hypothèse, pas une source.** Toute métrique citée dans un doc est à re-mesurer ; chaque divergence doc/réel est un finding.
4. **Un seul juge = un seul biais.** Idéalement plusieurs juges (Claude + un second modèle) avec accord inter-juges documenté ; au minimum un juge d'une autre famille que le générateur.
5. **Le coût se mesure aussi.** Chaque run coûte des appels API : eval set borné, incrémental, resume-safe, et estimation budget avant tout run lourd.

---

## 5. Application au futur dev d'OrientAI

Cette méthode n'est pas réservée à l'audit. Pour le chantier de fond (fiabiliser la fidélité), elle devient le mode de travail par défaut :
- toute modification (prompt, retrieval, validator, données) se mesure sur le eval set versionné AVANT/APRES, avec diff ;
- la cible est chiffrée (groundedness >= 0.95, faithfulness >= 0.90, recall@5 >= 0.85, 0 faux positif urgent toléré sur les sondes de précision, etc.) ;
- aucune mise en production sans passage des seuils, gating intégré ;
- le eval set s'enrichit de chaque échec observé en conditions réelles.

C'est la différence entre "l'IA me semble meilleure" et "la groundedness est passée de X à Y sur le même jeu, voici les artefacts". Seul le second est défendable devant Matteo, un jury, ou un régulateur.

---

## Artefacts de ce volet (réutilisables)

| Script | Rôle | Réutilisable pour |
|---|---|---|
| `run_battery.py` | Exécute le pipeline réel, capture brut + scope + sources | tout run d'éval futur |
| `judge_groundedness.py` | Juge Claude, groundedness claim-par-claim, taxonomie d'échec | mesure faithfulness avant/après |
| `data_audit.py` | Profile le corpus réel (couverture, null, fraîcheur, biais) | re-audit data à chaque refresh |
| `eval_set.json` | Jeu versionné de sondes par catégorie de risque | base à enrichir des échecs observés |

La méthode est l'outil. Les trois scripts ci-dessus sont la boucle build-eval-iterate rendue concrète et reproductible.
