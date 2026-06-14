# Verdict vérif-d'abord — Salaires InserSup BUT / Licence / Ingénieur

Ordre : 2026-06-14-1337-claudette-orientai-salaires-insersup-verif-dabord
Auteur : Claudette · Date : 2026-06-14 · Read-only (probe jointure, ZÉRO ingestion).

---

## TL;DR — NO-GO (sauf ingénieur marginal ~7%)

La data salaire EXISTE dans InserSup pour ingé/licence/LP (établissement + national),
mais **la JOINTURE depuis les fiches corpus échoue**. La prémisse "même dataset que les
masters" est vraie pour la DATA, FAUSSE pour la JOINTURE : les masters ont marché parce
que MonMaster porte la DISCIPLINE + un libellé de mention propre qui matche InserSup.
BUT/Licence/Ingé vivent sur des fiches PARCOURSUP : UAI seul, noms génériques/divergents,
PAS de discipline -> l'exact-match normalisé (méthode sûre zéro-fuzzy de C2b) ne trouve
quasi rien.

| Bucket | Salaire dispo (source) | Match join réel | Verdict |
|---|---|---|---|
| **BUT** | **0** (nd partout, étab ET national) | 0% | **NO-GO dur** (data inexistante) |
| **Licence générale** | étab 13% / national 54 libellés | étab 0%, national 0% | **NO-GO** |
| **Licence pro** | étab 15% / national 150 | 0.8% | **NO-GO** |
| **Ingénieur** | étab 44% / national 493 | **7.3%** (138 fiches, qualité mixte) | marginal / conditionnel |

---

## 1. Data disponible (lignes "ensemble", après masquage nd seuil 20)

Le CSV local `data/raw/insersup.csv` (568 Mo) contient bien les 4 types nativement :
BUT 16244 lignes brutes, Licence pro 205215, Licence générale 133957, Ingénieur 118302.
MAIS après filtre ensemble + salaire non-nd :

Établissement × discipline (lignes ensemble, salaire dispo / nd) :
- master 4315 / 14035 (24% dispo) · ingénieur 2880 / 3720 (44%) · licence_pro 1447 / 8278
  (15%) · licence 1101 / 7351 (13%) · **BUT 0 / 709 (0% — tout masqué nd)**.

Maille NATIONALE (Établissement="National", 6671 lignes, clé = libellé à "Tous domaines
disciplinaires", PAS par discipline) — cellules avec salaire :
- ingénieur 1188 · master 697 · licence_pro 433 · licence 158 · **BUT 0 / 28**.

**BUT est mort des deux côtés** : créé en 2021, cohortes trop récentes/petites -> aucune
valeur publiée (nd systématique). Aucune jointure ne le sauvera.

## 2. Pourquoi la jointure échoue (la vraie cause)

| Clé testée | ingé | licence | LP | BUT |
|---|---|---|---|---|
| Exact (UAI/etab + bucket + libellé canon) = méthode C2b | 0% | 0% | 0% | 0% |
| UAI + bucket seul (any libellé) — plafond, ambigu | 7% | 62% | 3% | 0% |
| National (bucket + libellé canon) | 7.3% | 0% | 0.8% | 0% |

- **Exact-libellé = 0% partout** : le nom de fiche parcoursup ne canonise pas comme le
  libellé InserSup. Ingé : noms GÉNÉRIQUES ("Formation d'ingénieur Bac+5") sans discipline
  -> rien à matcher. Licence : "Licence - Science politique" vs libellés InserSup, et le
  national ne publie que 54 libellés licence (vs 3294 fiches) -> 0 recouvrement.
- **UAI + bucket seul** : plafond modeste (licence 62% mais AMBIGU — un établissement a
  plusieurs licences de disciplines différentes -> on ne sait pas quel salaire attribuer
  sans la discipline. Attribuer = mal-attribuer. Précision > rappel l'interdit).
- **National** : 7.3% ingé seulement (et dont des "CYCLE PREPARATOIRE INTEGRE" qui
  récupèrent le salaire ingé bac+5 = faux). Licence/LP ~0 (libellés nationaux ne couvrent
  pas le corpus). BUT 0.

Racine : MonMaster (masters) = discipline + mention propre -> join sûr. Parcoursup
(BUT/Licence/Ingé) = UAI + nom générique sans discipline -> pas de clé sûre vers InserSup
(établissement × type × **discipline**).

## 3. Échantillon (les seuls matches : ingé national)

```
ingenieur | Ingénieur diplômé de l'ECAM-EPMI        | 2560€ | INGENIEUR DIPLOME DE L'ECAM-EP
ingenieur | Ingénieur diplômé de l'Ecole Centrale.. | 2820€ | INGENIEUR DIPLOME DE L'ECOLE C
ingenieur | cycle préparatoire intégré - prépa...   | 2480€ | CYCLE PREPARATOIRE INTEGRE   <- FAUX (prépa ≠ diplôme ingé)
```
Les matches école-nommée sont cohérents ; les "cycle préparatoire intégré" reçoivent à
tort le salaire ingé. Licence/LP/BUT : 0 match à montrer (c'est le finding).

## 4. Verdict go/no-go

- **NO-GO** pour BUT (data inexistante), Licence générale, Licence pro (jointure ~0,
  précision impossible sans fuzzy/discipline-mapping risqués).
- **Ingénieur : GO marginal CONDITIONNEL** seulement si on accepte ~138 fiches (7%) via
  national-libellé AVEC un garde-fou excluant les "cycle préparatoire intégré" (sinon
  faux positifs). Effort modéré, gain faible. À mon avis : pas prioritaire pré-VivaTech.
- **Effort full build** : élevé pour un rendement quasi-nul en haute précision. La
  méthode masters ne transfère PAS.

## 5. Recommandation

1. Ne PAS builder l'ingestion BUT/Licence/LP : rendement haute-précision ~0.
2. BUT : parquer indéfiniment (aucune donnée publiée, nd systématique seuil 20).
3. Le seul débloqueur réel = un mapping fiche parcoursup -> discipline/libellé InserSup
   (pour join UAI + discipline). C'est un sous-chantier à part, non-trivial (taxonomie,
   comme secteur), avec risque de mal-attribution -> vérif-d'abord dédiée AVANT, pas
   maintenant.
4. Fallback déjà en place : le proxy PCS encadré RÈGLE 6 couvre déjà le salaire des
   formations non-master sans trou nouveau. C'est la bonne réponse par défaut.

## 6. Méthode

build_salary_index (module C2b existant, déjà multi-bucket) + scan ciblé du CSV (lignes
ensemble, masquage nd via _NULL_TOKENS) + test de 3 clés de jointure sur les fiches corpus
eligible BUT/Licence/Ingé. Zéro ingestion, zéro modif.
