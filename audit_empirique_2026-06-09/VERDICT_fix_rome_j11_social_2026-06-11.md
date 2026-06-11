# Verdict — Fix mapping ROME J11 (travail social) + VAE judge-side

Ordre : 2026-06-11-1840-claudette-orientai-fix-data-rome-j11-voies-acces
Auteur : Claudette · Date : 2026-06-11 · Branche : `fix/rome-j11-social-mapping-order-1840`

---

## TL;DR

Deux bugs corrigés à la racine, prouvés par-question de façon déterministe, **sans
toucher l'index FAISS figé** (pas de ré-embed → baseline retrieval 497q intacte) :

- **Fix 1 (corruption data réelle)** : 409 formations de TRAVAIL SOCIAL (CESF, AES,
  éducateurs spécialisés, assistants de service social...) classées à tort
  `domaine=sante` héritaient des 10 débouchés ROME médicaux J11xx (médecin,
  sage-femme, infirmier, kiné...). Corrigé : `domaine=social` + débouchés ROME K*
  (travail social). C'est la cause racine de `detresse-prec-007`.
- **Fix 2 (mismatch instrument juge/générateur)** : la normalisation `voies_acces`
  "Par expérience" → VAE existait déjà côté GÉNÉRATEUR (chantier C2a, 09/06,
  `FactCard.dispositifs_reconversion`) mais le JUGE ne voyait que le `voies_acces`
  brut ("Par expérience"), d'où il pénalisait à tort "accessible en VAE". On expose
  au juge la même chaîne canonique.

---

## Root cause

### Fix 1 — chaîne du bug (multi-locus, chokepoint unique)

```
NSF 332 "Travail social"  ─┐
parcoursup "d.e secteur social" ─┤→ domaine="sante" → attach_debouches()
labonnealternance (ROME)  ─┘                          → get_debouches_for_domain("sante")
                                                       → 10 ROME médicaux J11xx
```

`_NSF_CODE_TO_DOMAIN["332"]="sante"` (merge.py) collapsait le travail social (NSF 332,
distinct de 331 Santé / 344 Techno médicales) dans la santé. `attach_debouches` est
le **chokepoint unique** où les J11xx sont injectés.

Témoin `detresse-prec-007` (groundedness 0.75) — la fiche S3 :
```
Conseiller en économie sociale familiale (rncp, bac+3)
  domaine = sante
  debouches = [J1102 médecin, J1104 sage-femme, J1201 paramédical, J1501 infirmier, ...]
```
Le juge : « S3 liste des débouchés ROME exclusivement médical/santé. L'affirmation
[débouchés social/éducation] généralise au-delà des sources » → hallucination flaggée.
**La donnée corpus était fausse, pas la génération.**

### Fix 2 — juge semi-aveugle (même pattern que Bloc A / instrument)

Le système a deux représentations de sources :
- GÉNÉRATEUR : `FactCard` → `_summarize_voies_acces()` map "Par expérience" → "VAE
  (validation des acquis de l'expérience)" (C2a, déjà testé : test_fact_card.py 674-803).
- JUGE (`run_battery._extract_fiche`) : copiait le `voies_acces` BRUT. Le juge voyait
  "Par expérience" sans jamais voir "VAE" → flaguait l'inférence pourtant correcte.

---

## Périmètre mesuré (corpus réel 52040 fiches)

| Mesure | Valeur |
|---|---|
| Fiches `domaine=sante` | 1737 |
| Fiches avec débouchés médicaux J11xx | 1737 (= le "1733" du brief, corpus a grossi) |
| **Reclassées sante → social (prédicat déterministe)** | **409** |
| Faux positifs médicaux (fiche médicale perdant ses débouchés santé) | **0** |
| Restent `sante` (vraie santé/paramédical) | 1328 |

Prédicat `is_social_work_formation` : multi-mots/acronymes spécifiques (AES, CESF,
éducateur spécialisé, assistant de service social, TISF, médiateur social, carrières
sociales, secteur médico-social...) + garde-fou paramédical (exclut infirmier,
aide-soignant, kiné... même avec un terme social). Tests : tests/test_merge.py.

Note : 409 vs ~392 estimé par l'audit Jarvis = prédicat production plus strict (évite
"sciences sociales") MAIS récupère les vrais faux négatifs (BUT Carrières Sociales,
médico-social), avec garde-fou paramédical. Set haute-précision.

---

## Preuve avant/après (déterministe, zéro coût juge)

Ré-extraction des sources figées du gel via l'instrument corrigé. Détail complet :
`results/measure_social_vae_before_after.txt`.

| Cas | Fix | Avant (vu par le juge) | Après (vu par le juge) | Claim flaggé |
|---|---|---|---|---|
| detresse-prec-007 S3 (CESF) | 1 | debouches = J11xx médicaux | debouches = K* (assistant social, AES, éducateur, TISF...) ; domaine=social | "débouchés dans le social" → **SUPPORTÉ** |
| detresse-prec-007 S3 | 2 | voies_acces brut "Par expérience" | dispositifs_reconversion "VAE ..." | "accessible en VAE" → **SUPPORTÉ** |
| reconv-001 S1 | 2 | "Par expérience" brut | "VAE ..." | **SUPPORTÉ** |
| reconv-004-v1 S7 | 2 | "Par expérience" brut | "VAE ..." | **SUPPORTÉ** |
| malform-004-v1 S2/S4/S5/S6/S7/S10 | 2 | "Par expérience" brut | "VAE ..." | **SUPPORTÉ** |

Sources marquées "toujours non" = celles qui n'ont QUE "formation continue" (≠ VAE) :
comportement correct, le claim VAE est porté par les autres sources de la réponse.

---

## Stratégie baseline-safe (contraintes ordre respectées)

- `debouches` et `domaine` sont DANS le texte embeddé FAISS ; `voies_acces` NON.
- **Pas de ré-embed** (opération Mistral >5$ → gatée Matteo) : l'index figé reste
  byte-identique → le retrieval du gel 497q est **intact**. Le contexte LLM (lu live
  depuis formations.json par fact_card) reflète immédiatement la correction.
- **Pas de re-run 497q** (~5$ juge → gaté). Preuve faite déterministiquement.
- Flip `domaine` sante→social vérifié **sans impact retrieval** : reranker et router
  lisent `fiche["domain"]` (type de corpus annexe), PAS `fiche["domaine"]` (thématique) ;
  `metadata_filter` filtre sur `secteur` (pass-through si absent, 0 fiche formation peuplée).

### Validation complète recommandée (GATÉE Matteo, post-merge)

Pour figer une nouvelle baseline cohérente : `python -m src.rag.embeddings` (ré-embed
~5-10$) puis re-run 497q + re-judge (~5$). Attendu : détresse-007 + les ~4 cas VAE du
tail remontent ≥0.7, hallucinations du tail en baisse, reste neutre. **À déclencher
seulement sur GO Matteo.**

---

## Anomalies latentes documentées (HORS SCOPE, candidats post-VivaTech)

1. **`fiche["domain"]` vs `fiche["domaine"]`** (signalé par Jarvis) : le reranker
   domain-aware (ADR-049) et le router lisent la clé anglaise `domain` (présente sur
   les corpora annexes : metier, crous, insee_salaire...). Les fiches FORMATIONS
   portent `domaine` (français) et n'ont pas `domain` → elles ne reçoivent **aucun
   boost domain-aware au retrieval**. C'est cohérent avec le commentaire
   "comportement formation-centric pré-ADR-049 préservé" mais signifie que la
   classification thématique (sante/social/data_ia...) ne pilote PAS le ranking des
   formations. Candidat : unifier `domain`/`domaine` ou câbler le boost thématique.

2. **Résidu faux négatif** : "Conseiller en transition professionnelle" (et formations
   d'insertion/orientation proches) restent `domaine=sante` avec débouchés médicaux —
   même classe de bug, hors prédicat précis (évité pour ne pas sur-élargir). Candidat
   pour un 2e passage avec validation manuelle.

3. **Régénération corpus** : `formations.json` est gitignored (régénéré, non versionné).
   La correction est appliquée localement (backup `data/processed/formations.json.bak-presocial-*`)
   ET inscrite dans le code (passe `reclassify_social_health` câblée dans run_merge_v3) →
   reproductible à la prochaine régénération via `python -m src.collect.run_merge_v3`.
