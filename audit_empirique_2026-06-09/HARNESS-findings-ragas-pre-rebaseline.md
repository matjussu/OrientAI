# Findings harnais Ragas - avant re-baseline post-C4 (2026-06-10, Claudette)

Demande Jarvis : root-cause des erreurs du run `ragas_full` + reco concrète de durcissement,
AVANT d'engager la re-baseline 497q (~5$). Critère : on ne lance pas 5$ sur un harnais à 36% d'erreur.

Tout ce qui suit est read-only / gratuit (aucun appel API facturé). Mesures faites pendant que
le PID 453274 tournait encore (non touché).

---

## 1. Le run en cours mesure le PRE-C4, pas le post-C4

`ragas_eval.py` score `results/battery_full.json`, une battery FIGÉE (497 records avec
`answer` + `sources` + `latency` déjà gelés), mtime **2026-06-09 14:14** -> antérieure à la
promotion C1 (soir du 09/06) ET au re-embed C4 (02:45 le 10/06). Les réponses + contextes
notés viennent donc de l'ANCIEN index. Conclusion : ce run est une **référence pré-C4 dégradée**,
il ne remplace pas la re-baseline. Classement à appliquer au verdict.

## 2. Taux d'erreur réel : ~36% des cellules (pas "quelques erreurs isolées")

Total jobs = 1158 = **386 samples gradeable** (filtre `in_scope` + `n_sources>0` + pas d'erreur,
ligne 59-61) **x 3 métriques** (faithfulness, answer_relevancy, LLMContextPrecisionWithoutReference).

| Classe d'erreur | Jobs distincts touchés | Métrique impactée |
|---|---|---|
| `TypeError(dict += dict)` | ~305 | **answer_relevancy** (quasi-totalité) |
| `TimeoutError` | ~113 | les 3 (aléatoire réseau) |
| "Temporary failure in name resolution" (events log) | 6815 | cause des timeouts |

Lecture par métrique du `ragas_full.json` final (à faire au verdict) :
- **answer_relevancy : INVALIDE** ce run (la majorité des 386 samples -> NaN, cf §3).
- **faithfulness + context_precision : exploitables** moins l'attrition réseau (~113 timeouts
  répartis sur les 3 métriques). Compter clean vs NaN PAR métrique, pas d'agrégat brut.

---

## 3. Classe 1 - `TypeError: unsupported operand type(s) for +=: 'dict' and 'dict'`

### Root cause (CONFIRMÉE empiriquement, repro déterministe sans API)

`langchain_mistralai 1.1.4` `ChatMistralAI._combine_llm_outputs` (chat_models.py:641-654) :

```python
for k, v in token_usage.items():
    if k in overall_token_usage:
        overall_token_usage[k] += v      # ligne 651 : dict += dict si v est un dict
    else:
        overall_token_usage[k] = v
```

- Le `token_usage` de Mistral contient maintenant des **sous-dicts imbriqués**
  (`completion_tokens_details`, etc.). Quand `v` est ce sous-dict, `overall[k] += v` =
  `dict += dict` -> TypeError.
- La branche `+=` n'est prise QUE si la clé est déjà vue, donc seulement quand on combine
  **>=2 générations**. `answer_relevancy` a `strictness=3` et appelle le LLM avec `n=3`
  (_answer_relevance.py:94,143) -> combine 3 outputs -> crash. faithfulness et
  context_precision tournent en `n=1` -> jamais la branche `+=` -> immunisés.
- Ce n'est PAS la cost callback de ragas (`ragas/cost.py`) : `evaluate()` ne l'attache que si
  `token_usage_parser` est passé (evaluation.py:221), or `ragas_eval.py` n'en passe pas.

Repro déterministe (pur dict, 0 API) : `_combine_llm_outputs(fake_self, [usage])` passe ;
`_combine_llm_outputs(fake_self, [usage, usage, usage])` -> TypeError exact. Avant/après fix vérifié.

### Fix APPLIQUÉ + TESTÉ (gratuit, dans le scope autonomie debug/test)

`src/observability/__init__.py` - nouveau **Step 1b** : remplace `_combine_llm_outputs` par un
merge profond qui somme les feuilles numériques et récurse dans les sous-dicts. Idempotent, no-op
si la lib est absente (venv prod). `token_usage` est ici du pur bookkeeping (ragas ne le consomme
pas faute de `token_usage_parser`) -> **zéro impact sur les scores de métriques**, ça empêche
seulement le crash. Élimine toute la classe 1 -> answer_relevancy redevient valide.

Test régression : `tests/test_observability_usage_combine.py` (4 cas, verts) - passthrough n=1,
no-crash + sommes correctes n=3, skip des outputs None (streaming), garde "patch installé".

> Note tracking : `src/observability/` est **non versionné dans git** (untracked sur toutes les
> branches, créé le 13/05, utilisé par tout le harnais + le décorateur `@observe` du pipeline).
> Le fix + le test vivent donc dans le working tree (comme le shim lui-même) et seront pris par
> la re-baseline via import. Reco hygiène séparée : committer tout `src/observability/` (décision
> Matteo, c'est de l'infra load-bearing actuellement à la merci d'un `git clean`).

---

## 4. Classe 2 - `TimeoutError` + 6815 "Temporary failure in name resolution"

### Root cause (CONFIRMÉE, deux causes réseau cumulées)

1. **DNS WSL flaky** : `/etc/resolv.conf` est le stub auto-généré par WSL (symlink ->
   `/mnt/wsl/resolv.conf`, `nameserver 10.255.255.254` = proxy NAT WSL). Sous charge concurrente,
   ce proxy renvoie par intermittence "Temporary failure in name resolution" (EAI_AGAIN).
   systemd-resolved est actif mais HORS du chemin (resolv.conf ne pointe pas sur 127.0.0.53).
2. **IPv6 cassé** : `getent hosts api.mistral.ai` renvoie d'abord des AAAA (Cloudflare,
   `2606:4700:...`), mais **WSL n'a pas de route IPv6** : un connect TCP 443 en IPv6 ->
   `Errno 101 Network unreachable`, alors que l'IPv4 (`172.66.2.203`) se connecte OK. Les tentatives
   IPv6-first stallent jusqu'au timeout.

Ces deux causes se cumulent et expliquent les 6815 échecs de résolution + 113 timeouts. Le
`max_workers=2` du run actuel (déjà un durcissement vs le 1er run à 228 timeouts) n'aide pas :
le problème est la résolution/route, pas la saturation API.

### Reco

**A. Race-day pour la re-baseline (primaire, AUCUN redémarrage, à retirer après) - nécessite Matteo (sudo)**
Pinner l'IPv4 du host Mistral dans `/etc/hosts` -> supprime le lookup DNS ET force l'IPv4 :
```
162.159.142.207 api.mistral.ai
```
(Couvre chat + embeddings, même host. IP Cloudflare anycast, l'autre A record `172.66.2.203` marche
aussi. À retirer après le run : les IP Cloudflare tournent, ne pas laisser en dur durablement.)

**B. Durable (post-VivaTech) - nécessite `wsl --shutdown` côté Windows, donc APRÈS la fin du run**
- `/etc/wsl.conf` : `[network] generateResolvConf = false`
- `/etc/resolv.conf` (dé-symlinker) : `nameserver 1.1.1.1` + `nameserver 8.8.8.8`
- Hygiène IPv6 : préférer l'IPv4 (gai.conf) ou désactiver l'IPv6 WSL tant qu'il n'y a pas de route.

Toutes les modifs de la classe 2 sont des changements système (hors scope autonomie Claudette) ->
proposition à Matteo, pas exécutées.

---

## 5. Séquencement proposé (aligné avec Jarvis)

1. Laisser finir le PID 453274. Lire `ragas_full.json` en comptant clean/NaN PAR métrique :
   answer_relevancy = invalide, faithfulness + context_precision = réf pré-C4 dégradée.
2. Fix classe 1 = **déjà appliqué + testé** (working tree). Fix classe 2 = `/etc/hosts` pin par Matteo.
3. Re-baseline post-C4 497q (~5$) au go Matteo, sur harnais durci (classe 1 corrigée + IPv4 pin).
   Régénérer la battery sur le nouvel index 52040 d'abord (sinon on re-score du pré-C4).
4. Re-mesure C2a vs baseline post-C4, verdict broderie, puis merge bloc corpus.

Critère de Jarvis respecté : avant de dépenser 5$, classe 1 est éliminée (testée) et classe 2 a un
fix sans redémarrage prêt à appliquer. On ne relance pas sur un harnais à 36%.
