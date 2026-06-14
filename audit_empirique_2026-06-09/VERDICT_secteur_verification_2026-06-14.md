# Verdict — Vérification activation du filtre `secteur`

Ordre : 2026-06-14-1306-claudette-orientai-secteur-verification
Auteur : Claudette · Date : 2026-06-14 · Read-only (aucune modif).

> Correction préalable : mon audit #140 classait secteur "gros poisson, plus gros
> que fili_code". **Je révise : c'est faux.** J'avais sur-rangé sur la présence des
> champs sans vérifier la compatibilité des taxonomies ni l'état du filtre. Verdict
> réel ci-dessous : gain INCERTAIN, conditionné à une table de correspondance, pas
> un "free win". Même erreur que les 2 fills 1305 (présence ≠ signal exploitable).

---

## TL;DR

**Gain net : INCERTAIN, conditionnel — PAS un free win.** Trois obstacles :
1. **3 taxonomies incompatibles** (le filtre veut des slugs canoniques, les sources
   donnent 2 autres nomenclatures) → table(s) de correspondance OBLIGATOIRE(S).
2. **Le filtre est DÉJÀ soft (pass-through)** : le problème "0 fiche peuplée" est déjà
   neutralisé. Activer ne débloque pas un refus, ça ajoute une exclusion sélective.
3. **Asymétrie** : ne peupler que monmaster + ideo rend CES sources filtrables alors
   que parcoursup/rncp/onisep restent immunisés → risque de biais (masters pénalisés).

Reco : si poursuivi, mini-chantier SÉPARÉ avec table disciplinaire→slug (monmaster
seul d'abord) + A/B obligatoire avec check de régression sur l'inclusion des masters.
Priorité revue à la BAISSE. Pas dans le ré-embed groupé des fills purs.

---

## 1. Cohérence des taxonomies — TROIS vocabulaires, aucun aligné

| Source | Champ | Vocabulaire | Exemples |
|---|---|---|---|
| **Filtre / RouterLLM** (la cible) | `criteria.secteur` | **slugs canoniques** | informatique, securite, sante, droit, commerce, ingenierie, art, sport, education, finance... (router_llm.py:532, INTERESTS_TO_SECTORS) |
| monmaster | `secteur_discipline` | **disciplinaire MESR** | "Sciences de gestion", "Sciences juridiques", "Informatique", "Histoire", "STAPS" |
| insersup | "Secteur disciplinaire" | **disciplinaire MESR** (= monmaster) | idem |
| onisep_ideo | `secteurs` | **économique/métier** | "Automobile", "BTP", "Santé", "Énergie", "Fonction publique", "Banque-Assurances" |

Conséquence : un copier-coller `secteur_discipline -> secteur` ne matche RIEN (le
RouterLLM cherche "droit", la fiche dirait "Sciences juridiques"). Il faut :
- **Table A** disciplinaire→slug (~40 entrées). Plutôt propre ("Informatique"→informatique,
  "Sciences juridiques"→droit) mais ambiguïtés réelles ("Pluridisciplinaire lettres,
  langues, sciences humaines"→ ? ; "Sciences de gestion"→commerce ou finance ?).
- **Table B** économique→slug pour ideo. Plus difficile : les slugs sont disciplinaires,
  pas économiques ("Automobile"/"BTP"→ingenierie ? gap sémantique).
- **INTERESTS_TO_SECTORS lui-même est incomplet** (commentaire code : "à enrichir au fil
  des logs", "risque mapping incomplet"). Le 3e maillon est déjà fragile.

Mélanger les 2 taxonomies dans un seul champ `secteur` produirait un mix incohérent
("Sciences de gestion" à côté de "Automobile"). À NE PAS faire.

## 2. Usage réel — le chemin est LIVE mais inerte

- `enable_router_llm=True` + `use_metadata_filter=True` par défaut (factory.py:109/116).
- Le RouterLLM (Mistral Small) émet `criteria.secteur` en slugs depuis la question
  (router_llm.py:292-302 ; ex ligne 594 : "écoles d'ingé cyber en Bretagne" →
  secteur=["informatique","securite"]).
- **Mais `_match_secteur` est pass-through** (metadata_filter.py:298-333) : une fiche
  sans `secteur` est supposée compatible avec n'importe quel secteur demandé. Conçu
  ainsi en 2026-05-09 PARCE QUE 0/15764 formations avaient secteur (sinon le filtre
  strict produisait des "Je n'ai pas de formation..."). Donc aujourd'hui le filtre
  secteur ne retire JAMAIS rien.

Ce qui change si on peuple : les fiches TAGGUÉES qui ne matchent pas le secteur demandé
seront EXCLUES post-rerank ; les non-tagguées continuent de passer. Ce n'est pas
"débloquer un refus", c'est "ajouter une exclusion sélective sur les sources tagguées".

## 3. Risque de sur-contrainte

- **Fiches non tagguées : SÛRES** (pass-through déjà codé). Pas de "0 résultat".
- **Fiches tagguées : RISQUE** d'exclusion à tort si la table disciplinaire→slug rate
  un cas (un master "Sciences cognitives" exclu d'une requête "informatique"/"sante").
- **ASYMÉTRIE (le vrai risque)** : ne peupler que monmaster (7573) + ideo (1075) rend
  ces sources filtrables alors que parcoursup/rncp/onisep restent immunisés. Sur une
  requête à secteur, les masters peuvent être systématiquement pénalisés (exclus si
  hors-secteur) pendant que des BTS/licences équivalents passent toujours → biais vers
  les sources non-tagguées. Soft (pas de refus dur) mais ça reshape le ranking/inclusion.

## 4. Estimation du gain (avec exemples)

Pertinent UNIQUEMENT sur les questions où le RouterLLM émet secteur (questions
intérêt/métier). Sur les autres (formation nommée, géo, calendrier...) : zéro effet.

- **Aide** : "je veux un master en droit" + secteur=["droit"] → exclut les masters
  monmaster hors-droit qui ont fui dans le top-K. Net si la table mappe bien.
- **Nuit** : "informatique" exclut un master "Sciences cognitives" pertinent si la
  table rate le mapping cognition→informatique/data.
- **Plafond** : `discipline` est DÉJÀ dans le BM25 (retrieval lexical) ; le retrieval
  sémantique+lexical surface déjà les fiches topiquement proches. Le gain MARGINAL du
  filtre par-dessus le retrieval peut être faible. Le filtre discrimine ; il n'ajoute
  pas de rappel.

## 5. Protocole A/B (probes ciblées, PAS 497q)

Activable et mesurable SANS ré-embed : `apply_metadata_filter` lit `fiche["secteur"]`
en live post-rerank → peupler secteur + reload = testable immédiatement ($0).

- ~12 probes déclenchant secteur via RouterLLM : "formations en informatique",
  "métiers de la santé quelle formation", "écoles d'ingé cyber Bretagne", "je
  m'intéresse au droit", "master en finance", "data science quelle voie"...
- Build A = corpus actuel (secteur vide). Build B = monmaster tagué disciplinaire→slug.
- Mesure : (a) pertinence du set de réponses (gain on-secteur / baisse off-secteur) ;
  (b) **check de régression EXPLICITE** : un master pertinent est-il exclu à tort par
  l'asymétrie ? Compter les masters droppés du top-K entre A et B.
- Jugement : manuel sur les 12 probes (ou juge sur ce sous-ensemble), pas le 497q.

## 6. Verdict

| Axe | Conclusion |
|---|---|
| Gain net | **INCERTAIN**, conditionné à une table de correspondance correcte + zéro régression d'asymétrie. Pas un free win. |
| Effort | **MOYEN** : table A disciplinaire→slug (~40, hand) + (optionnel) table B éco→slug + enrichir INTERESTS_TO_SECTORS + A/B bench. La table EST le travail et le risque. |
| Risque | Exclusion à tort (mapping imparfait) + biais d'asymétrie (masters pénalisés). SOFT (pas de refus dur), donc borné et réversible. |
| Reco | (1) NE PAS unifier les 2 taxonomies dans un champ ; mapper chacune → slugs via 2 tables séparées. (2) Commencer monmaster-disciplinaire→slug SEUL (le plus propre), laisser ideo-économique pour plus tard. (3) A/B obligatoire AVANT prod avec check régression masters. (4) Garder le flag `secteur_strict` (déjà anticipé code) pour réversibilité. (5) **Mini-chantier SÉPARÉ et mesuré, PAS dans le ré-embed groupé des fills purs. Priorité revue à la baisse vs mon #140.** |

Pourquoi je rétrograde mon propre classement : le "gros poisson" supposait un copier-coller
de 8600 signaux. En réalité : 3 taxonomies à réconcilier, un filtre déjà soft (donc pas
de blocage à débloquer), et une asymétrie qui peut régresser. Le gain existe peut-être
sur les questions intérêt/métier, mais il doit être PROUVÉ par A/B, pas supposé.
