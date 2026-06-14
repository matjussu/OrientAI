# Verdict vérif-d'abord — ROME 4.0 (France Travail)

Ordre : 2026-06-14-1347-claudette-orientai-rome-verif-dabord
Auteur : Claudette · Date : 2026-06-14 · Read-only (le ZIP est déjà local : `data/raw/rome_4_0.zip`).

---

## TL;DR — GO, mais en fact_card SEULEMENT, et HORS du ré-embed

Contraste avec le salaire (NO-GO) : ici la jointure est sur le CODE ROME =
**déterministe, 100%**. Mais 2 nuances cadrent le GO :
1. La moitié du contenu ROME 4.0 (compétences, savoirs) est **DÉJÀ dans le corpus**
   (rome_api_v4). Le vrai delta = **passerelles** + **RIASEC** + flags transition.
2. **ROME est MASQUÉ du dense** (fiche_to_text) — régression prouvée Run 5 / ADR-033.
   Donc l'enrichissement va en **fact_card (serve-time)** uniquement → $0, **PAS besoin
   du ré-embed**. Ne doit PAS gater le ré-embed des fills prouvés : on fige sans lui,
   on l'ajoute après quand on veut.

C'est une FEATURE (contenu citable d'orientation), pas un fix de retrieval.

---

## 1. Jointure — déterministe, 100%

- Le ZIP ROME 4.0 local couvre 1584 codes ROME. La table mobilité
  (`unix_rubrique_mobilite_v460_utf8.csv`, 14913 arêtes) donne des passerelles
  sortantes pour **les 1584 codes (100%)**.
- Corpus : 1584 fiches métier `rome_api_v4` → **1584/1584 ont des passerelles** (join
  parfait sur code_rome). 1631 codes ROME distincts référencés au total dans le corpus,
  1584 avec passerelles (les 47 restants = codes obsolètes → restent vides).
- Aucune ambiguïté de jointure (≠ salaire). Le code ROME est l'identifiant exact.

## 2. Contenu réellement AJOUTÉ (vs déjà présent)

| Donnée ROME 4.0 | Déjà dans le corpus ? | Verdict |
|---|---|---|
| Compétences (`competence`) | OUI — rome_api_v4.competences_par_enjeu | **REDONDANT, skip** |
| Savoirs (`savoir`) | OUI — rome_api_v4.savoirs_par_categorie | **REDONDANT, skip** |
| **Passerelles / mobilité** | NON | **NOUVEAU — la vraie valeur** |
| **RIASEC** (riasec_majeur/mineur, 1584) | NON | NOUVEAU (matching intérêts AnalystAgent) |
| **Flags transition** (eco/num/demo, réglementé, cadre) | NON | NOUVEAU (métadonnée métier riche) |
| Définitions/textes | partiel (text rome_api_v4) | marginal |

Canal cible : **fact_card uniquement**. PAS dense (ROME masking, Run 5). PAS BM25
(passerelles = codes, valeur lexicale nulle ; risque de bruit). Donc gain = contenu
CITABLE au moment de la réponse, PAS un boost de retrieval.

## 3. Échantillon (passerelles lisibles — valeur pour un lycéen)

```
Pilote de ligne (N2102)   -> Agent technico-commercial, Commercial, Vendeur auto, Agent accueil tourisme
Chef boulanger (D1108)    -> Vendeur épicerie, Chef de rayon, Chef de cuisine, Pizzaïolo
Eleveur d'animaux (A1435) -> Educateur canin, Auxiliaire vétérinaire, Toiletteur, Soigneur animalier
Exploitant agricole (A1416)-> Conseiller technique, Chargé de mission, Chef de culture
```
Ce sont de vraies trajectoires de mobilité/reconversion. Valeur orientation réelle :
"avec ce métier, vers quoi puis-je évoluer / me reconvertir ?". RIASEC ajoute le
profil d'intérêt (R/I/A/S/E/C) par métier — utile pour le matching intérêts->métiers.

## 4. Verdict go/no-go

- **GO** pour passerelles + RIASEC + flags transition → fact_card. Join 100%, valeur
  réelle, données publiques (Licence Ouverte, ZIP déjà local, zéro auth).
- **SKIP** compétences/savoirs (redondants avec rome_api_v4).
- **Couverture** : 1584 fiches métier enrichies directement. Option transitive (les
  11724 formations via leur codes_rome -> passerelles du métier cible) = possible mais
  à scoper prudemment (une formation pointe plusieurs métiers -> bruit) ; phase 2.
- **Effort** : modéré (parser 2-3 CSV du ZIP : mobilité, riasec, code_rome flags ;
  build code->data ; format fact_card). Pas de re-embed.
- **Inclus dans le ré-embed ?** : **NON.** fact_card est serve-time ($0). À découpler
  totalement du ré-embed des fills. On fige le set prouvé, on ajoute ROME après.

## 5. Gotchas

1. **NE PAS mettre ROME dans fiche_to_text** (régression Run 5, ADR-033, masking
   intentionnel). C'est LA contrainte dure. fact_card only.
2. Passerelles = code->code : besoin de code->libellé (le référentiel le fournit) pour
   être lisible/citable.
3. 47 codes corpus sans passerelles (obsolètes) → vides, pas d'invention.
4. Enrichissement transitif formation->métier->passerelles = bruit potentiel
   (multi-métiers) → métier fiches d'abord, formations en phase 2 si valeur prouvée.

## 6. Méthode

Lecture directe de `data/raw/rome_4_0.zip` (29 CSV référentiels v460). Test jointure
code_rome corpus<->ROME 4.0 sur la table mobilité + RIASEC. Zéro ingestion, zéro modif.
