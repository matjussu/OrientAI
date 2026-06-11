# Audit du finding "juge-aveugle / catégorie rubrique manquante" (J3, étape 1)

Date 2026-06-11. Auditeur : Claudette. Objet : vérifier, AVANT toute modif de rubrique,
si les "régressions" du gate Option B (substitution flag 7->15, answered_unsupported 2->8)
sont de vraies régressions de faithfulness OU des artefacts de rubrique (alternative
explicitement cadrée + sourcée que le juge n'a pas de catégorie pour classer).

Méthode : relecture des sorties brutes `results/ob_battery_after.json` + `ob_ground_after.json`
(48q SELECT = 12 questions de base x 4 paraphrases base/v1/v2/v3, génération temp=0, juge Haiku
temp=0). Attribution par-question, pas agrégat.

## Verdict : finding de Jarvis CONFIRMÉ (et renforcé)

**Les 17 cas "régressifs" (substitution flag OU outcome unsupported/substitution) ont TOUS :
`groundedness = 1.0`, `n_supported == n_claims` (zéro claim non supportée), `hallucinated_numbers = False`.**

Zéro échec réel de faithfulness. Aucun chiffre fabriqué, aucune affirmation non sourcée.
Les 8 nouvelles substitutions + 6 nouveaux unsupported de l'Option B = 100% artefacts de rubrique.

### Preuve smoking-gun : 4 paraphrases d'une même question, réponses quasi identiques, outcomes divergents

**Famille fact-006** (BTS Commerce International à Nantes ABSENT ; seule fiche = Papeete) :
même disclaimer ("Je n'ai pas... à Nantes. Seule fiche : Papeete 25% [S1]"), même source unique,
groundedness 1.0 partout, tous claims supportés. Outcomes :
- fact-006    -> answered_unsupported (subst=True)
- fact-006-v1 -> answered_grounded     (subst=False)
- fact-006-v2 -> answered_unsupported (subst=False)
- fact-006-v3 -> answered_grounded     (subst=False)

**Famille fact-011** (MIASHS à Annecy ABSENT ; Grenoble 98% / Lyon 78% existent) :
même disclaimer, mêmes alternatives sourcées, groundedness 1.0 partout. Outcomes éclatés sur
TROIS buckets :
- fact-011    -> answered_unsupported
- fact-011-v1 -> answered_grounded
- fact-011-v2 -> metric_substitution
- fact-011-v3 -> answered_unsupported

### Renforcement : contradiction interne dans les enregistrements du juge

8 cas (TOUS les answered_unsupported du run after : adv-004-v3, comp-008-v2, fact-006, fact-006-v2,
fact-008-v1, fact-011, fact-011-v3, fact-013) portent `outcome = answered_unsupported` ALORS QUE le
même enregistrement déclare `groundedness = 1.0`, `n_supported == n_claims`, chaque claim
`supported_by_sources = true`. (Recompte croisé Jarvis : 8 ; mon "9" initial était un sur-comptage,
corrigé — le run after compte exactement 8 answered_unsupported, tous auto-contradictoires.)
Or la rubrique définit answered_unsupported = ">=1 claim non supportée". Le label est donc
LOGIQUEMENT IMPOSSIBLE sous la définition propre du juge. Le juge ne trouve pas de claim non
sourcé : il cherche un label "n'a pas répondu à la question littérale" et attrape `unsupported`
ou `substitution` de façon interchangeable, faute de catégorie adéquate.

### Le comportement de génération est BON

Pattern uniforme sur les 17 : disclaimer explicite ("Je n'ai pas X à <lieu> dans mes sources")
+ alternative 100% sourcée ("voici Y [source SN]") + relance ("Veux-tu d'autres régions ?").
C'est exactement le fall-through souhaité. La fiabilité est parfaite ; seul le LABEL est faux.

## Contre-proposition / raffinements (droit exercé)

Je CONFIRME la catégorie `answered_alternative_disclaimed`. Trois précisions :

1. **Deux sémantiques de "substitution" dans le set, à distinguer dans les critères/tests :**
   - substitution de LIEU (fact-006/011/008/003) : même métrique, autre lieu, disclaimée+sourcée.
   - substitution de MÉTRIQUE (fact-013 : salaire demandé absent -> taux d'emploi à la place,
     marqué "en revanche"). C'est le cas-limite. Il reste faithful (disclaim explicite, sourcé,
     zéro prétention que le taux d'emploi EST le salaire) -> qualifie aussi answered_alternative_disclaimed.
     À inclure comme cas-test synthétique de bordure à l'étape 2.

2. **Faithfulness != Helpfulness — ne pas reconflater.** Offrir Papeete pour une demande Nantes
   (15000 km) est faithful mais peu utile ; offrir Grenoble/Lyon pour Annecy (même région) est
   faithful ET utile. La pertinence-de-l'alternative est un axe HELPFULNESS orthogonal. Le juge de
   groundedness ne doit PAS la noter (sinon on réinjecte la subjectivité qui a créé le bug).
   Recommandation : si on veut tracker la pertinence, un sous-flag `alternative_relevance` SÉPARÉ,
   HORS du gate faithfulness. Minimal pour l'ordre : ne pas l'ajouter au gate ; option à part.

3. **Garde-fou anti-gaming (à documenter dans la rubrique).** Cette catégorie n'est PAS un
   relâchement : elle ne re-bucket QUE des réponses dont le juge a lui-même prouvé groundedness=1.0
   + 0 claim non sourcé. hallucinated_numbers et la détection de claim non-supporté restent
   INTOUCHÉS : une alternative NON sourcée ou un chiffre fabriqué reste answered_unsupported.
   On corrige un label auto-contradictoire, on ne déguise pas du mauvais en bon.

## Impact attendu sur le gate (à CONFIRMER empiriquement à l'étape 3, non revendiqué ici)

Re-buckétés en answered_alternative_disclaimed, les 8 nouvelles substitutions + 6 nouveaux
unsupported disparaissent comme régressions. Restent : honest_refusal 35->20 (-15, vrai gain),
hallucinated_numbers 0->0 (sûr). Le gate Option B devrait passer de FAIL à PASS. NE PAS conclure
avant le re-jugement juge-only de l'étape 3 (mêmes artefacts, rubrique figée).

## Notes infra

- 2 pipeline_error dans le run after (fact-001-v2, comp-008-v1) = erreurs d'exécution du chemin
  fall-through, pas du juge. À gérer au re-jugement (re-générer ces 2q ou les exclure proprement).
- Rubrique à modifier = `audit_empirique_2026-06-09/judge_groundedness.py` (juge de l'audit),
  PAS `src/eval/judge.py` (fichier protégé, rubrique v1 figée pour comparaison longitudinale).
