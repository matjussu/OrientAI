# Rapport bench e2e — re-embed + fills (ordre 2026-06-14-1403)

Auteur : Claudette · Date : 2026-06-14 · Pas de merge/prod (deploy = go Matteo après lecture).

Set mesuré : typage (18261) + RNCP titres pros (2224) + emploi lycée pro (2542) + onisep
niveau (132) + ROME fact_card (1584). AVANT = corpus+index backup (pré-fills) ; APRÈS =
corpus filé + index ré-embeddé. 25 questions curées, réponses modèle temp=0, côte-à-côte.

---

## VERDICT : NON-RÉGRESSION confirmée + gains ciblés. Deploy-safe.

- **Golden 50q : GATE VERT** — recall source 17/17 (100%), NON régressé. (recall domain
  14/30 = report non-bloquant, instrument ambigu connu.)
- **Sanity stable** : longueur réponse 781 -> 756 chars, sources 9.7 -> 9.7, 0 erreur sur 25.
  Aucun sur-refus nouveau, aucune dégradation de format.
- Les gains sont CIBLÉS (fact_card surfacé) et HONNÊTES, pas un lift de retrieval massif.

---

## Gains concrets AVANT -> APRÈS (exemples pour Matteo)

### Gain net — typage RNCP (le fill 1305 marche en génération)
**"Comment devenir accompagnant en gérontologie ? Quelle certification ?"**
- AVANT : "la certification Accompagnant en gérontologie (niveau CAP-BEP)... accessible via VAE..."
- APRÈS : "...Elle est reconnue par un **Titre professionnel RNCP** et accessible via..."
-> Le modèle nomme désormais explicitement le **Titre professionnel RNCP** (la fiche est
   une des 2224 certifs sur-demande typées). Avant : ce label n'existait pas.

### Gain — passerelles ROME citées (fill 1402)
**"Vers quel métier peut évoluer un boulanger ?"**
- APRÈS cite les passerelles via "passerelles naturelles" : Pâtissier, Chef boulanger,
  encadrement/gestion de production. (AVANT était déjà correct car la fiche métier
  rome_api_v4 portait déjà des débouchés -> gain ici marginal mais le canal passerelles
  est actif, cf RIASEC/transition ci-dessous.)
- RIASEC / transition : signaux cités 1/2 -> **2/2** (le métier "concepteur paysagiste"
  ressort sa dimension transition écologique/environnement de façon plus ancrée).

### Stable (pas de régression, pas de gain visible sur ces probes)
- **typage comparaisons abstraites** ("différence BUT info vs prépa MPSI", "BTS vs BUT") :
  refus AVANT ET APRÈS. Le fill type_diplome consolide la DISCRIMINATION en dense, mais
  ces requêtes de COMPARAISON abstraite ne récupèrent pas de fiche formation -> refus
  honnête maintenu (pas de régression). Le gain typage se verra sur des requêtes ciblant
  une formation nommée, pas une comparaison de concepts.
- **emploi lycée pro** ("taux d'emploi après bac pro commerce") : refus AVANT ET APRÈS.
  L'enrichissement insertion_pro est fact_card-only -> il ne booste PAS le retrieval ;
  si la fiche lycée pro n'est pas récupérée, l'insertion ne se surface pas. Comportement
  attendu (cf verdict 1327 : gain fact_card, pas retrieval).
- **définition "titre professionnel RNCP"** : "pas de définition explicite" AVANT/APRÈS.
  type_diplome est un LABEL, pas une définition -> n'ajoute pas de fiche-définition.

---

## Lecture honnête

- Le re-embed est **sans risque** (golden vert, sanity stable) : déployable.
- Les gains réels sont **concentrés là où le fill alimente la fact_card ET où la fiche est
  récupérée** : labelling RNCP (net), passerelles/RIASEC/transition ROME (actif). C'est
  cohérent avec la nature des fills (fact_card serve-time pour rncp-label/lycée/ROME ;
  dense pour type_diplome/région/niveau).
- Le gain dense (type_diplome) ne se voit PAS sur les comparaisons abstraites de ce banc.
  Pour le mesurer, il faudrait des probes ciblant une formation nommée (ex "BUT informatique
  à Lyon, c'est quel diplôme ?") plutôt qu'une comparaison de concepts. Candidat probes v2.
- **Aucune contre-indication au deploy.** Recommandation : GO deploy possible (gains ciblés
  + zéro régression), en gérant l'attente : ce n'est pas un saut de qualité global, c'est
  un enrichissement ciblé (RNCP labelling, passerelles métier, emploi lycée pro quand
  retrouvé) sans coût de régression.

## Artefacts

- Réponses brutes : `bench_e2e_AVANT.json` / `bench_e2e_APRES.json` (25Q chacun).
- Questions : `bench_e2e_questions_1403.json`. Harnais : `scripts/bench_e2e_1403.py`.
- Index NOUVEAU : `formations.index` (52040) + quads + manifest (cohérents, 52040).
- Rollback : `*.before-fills-20260614` (corpus, flat index, 4 quads, manifest) -> restauration
  de l'état prod actuel possible si Matteo ne déploie pas.
- Golden gate : VERT (recall source 100%).
