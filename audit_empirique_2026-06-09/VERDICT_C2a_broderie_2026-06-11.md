# Verdict C2a (broderie) - re-mesure propre vs baseline post-C4

Date : 2026-06-11. Mesure : `run_c2a_measure.sh` sur index C4 (52040), juge Haiku temp=0.
BEFORE = fact_card.py @634189e (sans C2a) ; AFTER = HEAD (avec dispositifs_reconversion).
Artefacts bruts : `results/c2a_{battery,ground}_{before,after}.json` (28q chacun, accessibles recompte).

Note : re-mesure refaite a froid apres PURGE des artefacts stale du 09/06 (ancien index,
archives dans `results/_stale_c2a_oldindex_20260609/`). L'ancienne mesure etait invalide.

## Resultats

### Sous-ensemble voie d'acces (16q) - effet attribuable C2a
| metrique | before | after | delta |
|---|---|---|---|
| honest_refusal | 8 | 5 | -3 |
| answered_grounded | 4 | 6 | +2 |
| answered_unsupported | 4 | 5 | +1 |
| metric_substitution | 0 | 0 | 0 |
| hallucinated_numbers | 3 | 5 | +2 |
| mean_groundedness (asserting) | 0.679 | 0.720 | +0.041 |

### 28q complets (contexte, plafond ~16 ; 12q financement = C2b differe)
mean_groundedness 0.481 -> 0.513 ; honest_refusal 8 -> 5 ; substitution 0 -> 0.

## Verdict : broderie REELLE mais MINEURE, dominee par le gain

C2a est un net win : il debloque 3 refus en reponses (surtout VAE), monte la groundedness,
et ne cree AUCUNE substitution (confirme que reconversion != failure mode salaire).

Attribution par-question des nouvelles hallu (le test du verdict) :

- **C2a-attribuable (broderie du champ dispositifs_reconversion)** :
  - `reconv-002-v1` (1/3 phrasings VAE) : refus -> unsupported. Le modele brode la
    definition VAE + "1 an / 1 607 heures" + procedure (dossier recevabilite, livret 2,
    jury) depuis sa connaissance parametrique, non source. Les 2 autres phrasings
    (`reconv-002`, `reconv-002-v3`) passent refus -> grounded (corrects).
  - `reconv-007-v1/v2` (formation continue) : sur-attribution de la VAE a une formation
    precise (Manager RH CESI) dont la fiche ne liste PAS VAE dans voies_acces. Mild
    (outcome reste grounded), 1 claim non supporte chacune.

- **NON attribuable a C2a** :
  - `reconv-004*` (paramedical) : hallu sur durees de formation ("1 an", "2 ans") et
    descriptions de metiers (directeur ecole paramedicale, infirmier humanitaire).
    Pre-existantes (deja unsupported before), elaboration generale, pas le champ C2a.

Caveat methodo : subset n=16, run unique, generation temp>0 -> le delta agrege
(+2 hallu_num) comporte du bruit de generation. L'attribution par-question (qualitative,
juge temp=0) est le signal fiable : 1 cas net + 2 cas mild touchent dispositifs_reconversion.

## Reco

Broderie pas un blocker. Garde-fou additif anti-elaboration LEGER pour dispositifs_reconversion :
"n'expose que ce que la fiche liste dans dispositifs_reconversion ; ne definis pas la VAE de
memoire, ne decris pas sa procedure chiffree (duree/heures/livrets/jury) sauf si presente dans
les sources ; n'attribue un dispositif a une formation que si sa fiche le liste."

A BUNDLER avec le prompt garde-fou salaire (meme fichier system.py, cout marginal nul),
re-mesure sur ce meme subset C2a. Priorite a arbitrer par Jarvis (le focus ordre = salaire).
