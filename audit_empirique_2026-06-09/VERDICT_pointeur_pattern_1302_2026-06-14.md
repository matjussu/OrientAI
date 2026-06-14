# Verdict — pattern "honnêteté + pointeur" (ordre 2026-06-14-1302)

Auteur : Claudette · Date : 2026-06-14 · DESIGN + VÉRIF seulement (pas de build).

10 questions de catégories non-sourcées (frais privé/public/alternance, salaire non-master)
sur l'index deploy-candidate, génération temp=0.

---

## 1. Comportement ACTUEL (mesuré)

Le contrat v4 marche déjà bien sur la BASE : le modèle refuse honnêtement et ne sort pas
de chiffre inventé "au doigt mouillé". MAIS 3 défauts réels :

| Défaut | Preuve | Impact |
|---|---|---|
| **Pointeur GÉNÉRIQUE, pas précis** | frais privé/public -> "Onisep, Parcoursup, CIO" (jamais le site établissement, jamais InserSup/InserJeunes) | l'utilisateur n'est pas envoyé à la BONNE source |
| **Pointeur LLM-GÉNÉRÉ** | le modèle écrit lui-même "Onisep : https://onisep.fr" | vecteur d'invention d'URL (URL fausse possible) — exactement ce que la condition dure veut supprimer |
| **Proxy PCS = granularité trompeuse** | sal-ing "45 000€" (PCS 38 = médiane CARRIÈRE, pas sortie d'école ~38k) ; sal-but propose des salaires de MASTER ; sal-lyceepro donne PCS 55/22 (métier, pas insertion formation) | chiffre SOURCÉ mais répondant à une question subtilement différente |

Exemples bruts :
- frais-priv-01 (ESILV) : "Je n'ai pas d'information fiable... je te redirige : Onisep, Parcoursup, CIO" (honnête mais générique).
- sal-but-01 : "Je n'ai pas de BUT... Mes données concernent uniquement des masters... 2420€, 2850€" (offre du master quand on demande du BUT).
- sal-ing-01 : "ingénieurs PCS 38 : 45 000€" (médiane carrière servie pour "sortie d'école").

=> Le pattern pointeur n'est PAS un fix d'un truc cassé (la base est honnête), c'est une
amélioration de PRÉCISION + une suppression d'un vecteur d'invention (URL) + un garde-fou
sur la granularité PCS.

## 2. Design du MAP CURÉ déterministe (jamais LLM-généré)

Détection de catégorie = intent (frais/salaire, mots-clés déjà dans structured_select) ×
type/source de la fiche récupérée (type_diplome désormais REMPLI -> détection fiable).

```
POINTER_MAP (curé, statique, versionné) :
  frais_ecole_privee   -> "frais variables selon l'établissement"
                          + Parcoursup (fiche formation) + site officiel de l'établissement
  frais_public_univ    -> "droits d'inscription nationaux fixés par arrêté (hors CVEC)"
                          + service-public.fr/particuliers (droits d'inscription université)
  frais_alternance     -> "gratuit pour l'alternant + tu es rémunéré (employeur/OPCO)"  [fait structurel, pas d'URL]
  salaire_univ         -> "salaire formation pas dans mes sources à ce niveau"
   (licence/master/doc)   + InserSup MESR (data.enseignementsup-recherche.gouv.fr/.../fr-esr-insersup)
  salaire_bts_bacpro   -> idem + InserJeunes (inserjeunes.education.gouv.fr)
  salaire_metier       -> idem + France Travail métierscope (candidat.francetravail.fr/metierscope)
```

Règles dures du map :
- **100% statique/curé** : URLs officielles écrites à la main, versionnées dans le code.
  Le modèle ne génère JAMAIS l'URL ni la cible -> supprime le vecteur d'invention.
- Sélection par PRÉDICAT déterministe (intent × type_diplome/source), pas par le LLM.
- Déclenché UNIQUEMENT quand la valeur est absente (champ null) -> pas de sur-refus sur les
  fiches qui ONT la donnée.
- Le proxy PCS (RÈGLE 6) reste, mais le pointeur s'ajoute APRÈS pour donner la source
  PRÉCISE (et signale l'écart de granularité : "ceci est un salaire métier/carrière, pour
  l'insertion de la formation -> InserJeunes/InserSup").

## 3. Reco : GO conditionnel (incrémental, faible risque)

| Axe | Évaluation |
|---|---|
| Gain | RÉEL mais INCRÉMENTAL : pointeur précis (bonne source) + suppression du vecteur URL inventée + garde-fou granularité PCS. Pas un fix d'un truc cassé (la base refuse déjà honnêtement). |
| Risque | FAIBLE. (a) sur-refus : mitigé par "déclenche seulement si valeur absente". (b) mauvais pointeur : map keyé sur type_diplome/source remplis (déterministe, conservateur). (c) le map curé SUPPRIME le risque actuel d'URL LLM-inventée. |
| Effort | MODÉRÉ : post-process déterministe (comme strip_invented_urls) lisant intent + type/source -> append du pointeur curé. Pas de re-embed (post-génération). |
| Canal | Post-process déterministe (Sprint 8 wave 1 a déjà strip_invented_urls/validate_onisep_slugs) OU fact_card. PAS le LLM. |

### Sketch avant -> après (sal-but-01)
- AVANT : "Je n'ai pas de BUT... Mes données concernent des masters... 2420€" (offre du master, pointeur absent).
- APRÈS (avec map) : "Je n'ai pas le salaire d'insertion du BUT informatique dans mes sources. Pour cette donnée, consulte **InserJeunes** (inserjeunes.education.gouv.fr). [le proxy PCS métier reste possible, étiqueté]".

### Protocole A/B (si build)
- ~15 probes (frais privé/public/alternance + salaire univ/BTS/métier) + 10 probes de CONTRÔLE qui ONT la donnée (vérifier zéro sur-refus).
- Mesure : (a) pointeur précis présent (la bonne source citée) ; (b) zéro sur-refus sur le set contrôle ; (c) zéro URL hors-map ; (d) granularité PCS signalée.
- Génération seule, ancien vs nouveau comportement.

### VERDICT
**GO conditionnel**, priorité APRÈS le deploy prouvé (gain incrémental, pas urgent).
La vraie valeur : transformer un pointeur générique LLM-généré en pointeur PRÉCIS curé
déterministe, et cadrer le proxy PCS. Faible risque, effort modéré, déterministe (respecte
la condition dure). Si build : map curé + post-process + A/B avec set contrôle anti-sur-refus.
NO-GO si : on n'a pas le temps de maintenir le map curé à jour (URLs officielles changent) ou
si le proxy PCS actuel est jugé suffisant.

Artefacts : probes_pointeur_questions_1302.json, probes_pointeur_OUT.json.
