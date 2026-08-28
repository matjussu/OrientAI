# Bench OrientIA — 6 personas × 3 queries = 18 queries (2026-04-24)

**Contexte** : post D6 FAISS re-index sur corpus v2 48 914 fiches (pipeline v2 + Inserjeunes CFA intégré, rééquilibrage phase ADR-039).
**Notation** : humaine (Claudette), grille stricte 5 critères × 5 points.
**Modèle** : `mistral-medium-latest` + RAG FAISS 48 914 × 1024 dims.

---

## Tableau de notation synthèse

| # | Persona | Query | Type | Précision | Pertinence | Perso | Safety | Verbosité | **Moy** |
|---|---------|-------|------|:---------:|:----------:|:-----:|:------:|:---------:|:-------:|
| 01 | Lila (initial) | Débouchés L lettres modernes | factuelle | 3 | 4 | 2 | 5 | 4 | 3.6 |
| 02 | Lila | SHS fac vs école com | ambigu | 3 | 4 | 3 | 5 | 4 | 3.8 |
| 03 | Lila | 14 moy T L, écrire+histoire, pas prof | contextuel | 4 | 5 | 5 | 5 | 5 | **4.8** |
| 04 | Théo (réorient) | Passerelles L1/L2 droit → BTS/ESC | factuelle | 3 | 4 | 2 | 5 | 4 | 3.6 |
| 05 | Théo | Pas droit, pas redoubler, réaliste | ambigu | 3 | 4 | 4 | 3 | 3 | 3.4 |
| 06 | Théo | L2 droit, Bordeaux, audio/commerce alternance | contextuel | 3 | 4 | 5 | 5 | 4 | 4.2 |
| 07 | Emma (master-pro) | Salaire dev débutant M2 info | factuelle | 4 | 5 | 3 | 5 | 4 | 4.2 |
| 08 | Emma | M2 recherche vs alternance pour CDI | ambigu | 3 | 5 | 4 | 5 | 5 | 4.4 |
| 09 | Emma | Lille, data/ML, big tech vs startup, CDI | contextuel | 3 | 5 | 5 | 5 | 4 | 4.4 |
| 10 | Mohamed (voie pro) | Débouchés bac pro cuisine alternance | factuelle | 3 | 4 | 3 | 5 | 4 | 3.8 |
| 11 | Mohamed | CAP cuisine, pas restauration | ambigu | 3 | 5 | 4 | 5 | 4 | 4.2 |
| 12 | Mohamed | Marseille, bac pro alt, cuisine vs pâtisserie | contextuel | 3 | 5 | 5 | 5 | 4 | 4.4 |
| 13 | Valérie (parent) | Coût école com vs licence | factuelle | 4 | 5 | 4 | 5 | 5 | **4.6** |
| 14 | Valérie | STAPS débouchés ? | ambigu | 4 | 5 | 4 | 5 | 5 | **4.6** |
| 15 | Valérie | Fils T S, 13 moy, sport, pas moyens | contextuel | 3 | 5 | 5 | 5 | 4 | 4.4 |
| 16 | Psy-EN (pro) | Indicateurs master psycho clinique 3 ans | factuelle | 3 | 5 | 5 | 5 | 4 | 4.4 |
| 17 | Psy-EN | 1ère S redouble 7 maths, excellente philo | ambigu | 3 | 5 | 5 | 5 | 4 | 4.4 |
| 18 | Psy-EN | Élève 2nde modeste, rêve aéro, 10-11 maths | contextuel | 3 | 5 | 5 | 5 | 5 | **4.6** |

**Moyennes par critère (18 queries)** :
| Critère | Moyenne | Écart |
|---|:---:|---|
| Précision factuelle | **3.22** / 5 | Point faible majeur — hallucinations stats récurrentes |
| Pertinence conseil | **4.67** / 5 | Point fort — Plans A/B/C + tableaux comparatifs efficaces |
| Personnalisation | **3.94** / 5 | Moyenne — excellent sur contextuelles, faible sur factuelles |
| Safety | **4.89** / 5 | Point fort — warnings pièges systématiques, aucune discrimination |
| Verbosité / lisibilité | **4.22** / 5 | OK — parfois trop long pour factuelles simples |
| **MOY GLOBAL** | **4.19** / 5 | Bon baseline v2, mais défauts précision à traiter |

**Moyennes par type de query** :
| Type | Moyenne | Interprétation |
|---|:---:|---|
| Factuelle (6 queries) | 4.00 | Solide sur le cadre, mais faible précision stats |
| Orientation ambiguë (6 queries) | 4.13 | Bon sur tableaux comparatifs |
| Contextuelle riche (6 queries) | **4.47** | Point fort — le contexte fait exploser la qualité |

**Moyennes par persona** :
| Persona | Moyenne | Observations |
|---|:---:|---|
| Lila (17, T L) | 4.07 | Faible sur Q1 générique (factuelle peu personnalisée) |
| Théo (19, L2 droit) | 3.73 | ⚠️ Point bas — **retrieval mismatch** sur Q4 + Q5 (cf notes) |
| Emma (22, M1 info) | 4.33 | Bon score, retrieval moyen sur Q8 mais génération compense |
| Mohamed (17, CAP cuis.) | 4.13 | Inserjeunes CFA visible dans sources Q10 ✅ |
| Valérie (parent) | 4.53 | ⭐ Meilleur persona — factuelles précises + safety excellente |
| Psy-EN (pro) | 4.47 | Réponses niveau pro bien calibrées |

---

## Observations transversales

### 1. 🔴 **Précision factuelle : point faible n°1 — hallucinations stats plausibles**

Le système produit régulièrement des statistiques précises avec des sources plausibles qui ne sont **pas extractées du corpus retrieve** :
- **Q1** : "80% des débouchés qualifiés nécessitent master" (non sourcé)
- **Q8** : "90% des alternants en informatique sont embauchés" (cite "baromètre CEREQ 2023" — non vérifiable)
- **Q10** : "85% des diplômés trouvent un emploi en <6 mois"
- **Q12** : "100% des diplômés CDI en 6 mois — enquêtes régionales Paca"
- **Q15** : "1 étudiant sur 5 passerelle réussit kiné du premier coup — source FNEK" (citation de source mais non vérifiable)
- **Q18** : "Partenariat IUT Toulouse avec Airbus"

**Pattern** : le modèle invente volontiers des chiffres précis en ajoutant une source plausible (CEREQ, DEPP, FNEK, Welcome to the Jungle, baromètre Syntec). Classique de l'hallucination "citations fabrication" identifiée dans ADR-014 Run F+G.

**Point positif fort** : le système marque régulièrement `(connaissance générale)` quand il ne s'appuie pas sur le retrieve — c'est manifestement une consigne du system prompt v3.2 qui fonctionne dans ~70% des cas. Mais parfois il oublie et cite une source plausible.

**Action recommandée** : renforcer le system prompt avec une règle explicite "si une stat chiffrée n'est pas dans les sources retrievées, marquer `(connaissance générale)` ou ne PAS la donner". Potentiel +0.5 à +1 pt sur précision.

### 2. 🟡 **Retrieval mismatch sur les queries avec négation ou inversion logique**

Top-5 sources retrievées parfois **inversées vs intent** :
- **Q4** (Théo passerelles hors droit) : top-5 = Licence LEA, Brevets polyvalents, Diplôme économie-finance — **aucune passerelle explicite**. La génération a compensé.
- **Q5** (Théo "pas droit") : top-5 = 5× doubles licences droit/langues — **l'opposé du besoin**. La génération a ignoré les sources et répondu sur sa connaissance.
- **Q8** (Emma M2 rech vs altern) : top-5 = Conception lumière, Mode et matière, Gestion de Patrimoine — **aucun rapport avec info**. Score retrieval médiocre.
- **Q12** (Mohamed cuisine vs pâtisserie) : top-5 = 5× "Management Hôtellerie-Restauration Option B" — pas la bonne granularité.

**Diagnostic** : embeddings Mistral + fiche_to_text simple ne captent pas la négation ("pas droit", "pas restauration") ni les intentions de comparaison inter-diplôme. Le re-ranking compense peu.

**Action recommandée** (S+1) : tester ingestion de verbatims plus riches dans `fiche_to_text` (ajouter `debouches`, `insertion_pro.taux_*`), expérimenter un query rewrite en amont (intent classifier), ou re-ranker cross-encoder plus agressif sur les queries négatives.

### 3. 🟢 **Personnalisation : le contexte fait x1.5 la qualité**

Les queries contextuelles riches (Q3, Q6, Q9, Q12, Q15, Q18) ont une moyenne **4.47/5** vs factuelles **4.00/5**. Le système exploite très bien :
- Notes précises (14 moy → suggestions mention B, pas TB)
- Ville (Bordeaux → KEDGE, Marseille → Lycée Jean Capelle, Lille → OVH/Dataiku)
- Préférences (pas prof, pas restauration, CDI direct)
- Contraintes (modeste → public, pas école privée chère)

**Faiblesse** : les queries factuelles (Q1, Q4, Q7, Q10) n'exploitent pas le contexte persona (Lila 17 ans → réponse identique à ce qu'on donnerait à un adulte).

**Action recommandée** : le system prompt pourrait forcer un registre adapté au persona (âge, scope) sur les factuelles. Potentiel +0.5 pt sur personnalisation.

### 4. 🟢 **Safety : niveau très haut, aucun biais détecté**

- Warnings pièges **systématiques** : écoles privées non-RNCP, stats biaisées, promesses marketing trompeuses (Q1, 4, 5, 6, 10, 11, 13, 14, 15, 18).
- Mention Psy-EN / SCUIO / conseiller CEP en fin de plusieurs réponses — excellent pour public 17-25.
- **Zéro biais genre/origine sociale** détecté sur les 18 queries.
- Q15 (Valérie "pas les moyens") : le système **insiste sur les voies publiques gratuites** et alerte sur les prépas privées biaisées. Comportement éthique exemplaire.

### 5. 🟢 **Structure : TL;DR + 3 Plans + ⚠ + Question = pattern efficace**

Structure récurrente observée :
- **TL;DR** : 3 bullet points, donne la réponse en 10s de lecture
- **Plan A / B / C** : réaliste / ambitieux / alternative
- **⚠ Attention aux pièges**
- **Question pour toi** : pivot vers un échange

**Tableaux comparatifs** (Q2, Q8, Q12, Q15) sont les moments les plus forts — très efficaces pour l'orientation ambiguë.

**Défaut** : longueur non adaptée au type de query. Q1 "débouchés lettres modernes" = 1000+ mots pour une question factuelle simple. **Recommandation** : calibrer la longueur selon le type (factuelle ≤ 300 mots, ambigu ≤ 600 mots, contextuel ≤ 900 mots).

### 6. ✅ **Nouvelles sources v2 : intégration visible**

- **Inserjeunes CFA** visible dans sources top-5 de Q10 (Mohamed débouchés bac pro cuisine) — le rééquilibrage phase ADR-039 fonctionne.
- **InserSup DEPP** cité nominalement dans Q16 (Psy-EN master psycho clinique) — le modèle connaît la source mais ne l'utilise pas en citation directe.
- **Céreq, DARES** mentionnés en arrière-plan (connaissance générale) — pas activement retrievés mais connus du modèle.
- **Scores retrieval** avec v2 corpus sont cohérents (0.72-1.22 range, équivalent v1).

### 7. ⚠️ **Scope 17-25 et phases ADR-039 : couverture équilibrée**

- 3 phases couvertes : initial (Q1-3, 14-18 représentent ~50% des queries), réorientation (Q4-6, Q11 = 22%), master-pro (Q7-9, Q16 = 22%), voie pro (Q10-12 = 17%).
- **Pas de biais "segment mineur"** détecté : les queries voie pro/apprentissage (Mohamed) reçoivent les mêmes scores moyens que master-pro (Emma). Le corpus CFA 11k intégré apporte une granularité.
- **Warning subtil** Q1 : Lila 17 T L reçoit mentions "salaire médian après 5 ans" et "VAE après 3 ans d'expérience" — peu pertinent pour une personne qui n'a pas encore le bac. Anachronisme temporel.

---

## Verdict global : OrientIA baseline v2 = **4.19/5** — solide mais deux leviers clairs

### Points forts (à préserver)
1. ✅ Structure pédagogique (TL;DR + Plans A/B/C + ⚠) très efficace pour l'orientation
2. ✅ Personnalisation sur queries contextuelles riches (4.47/5)
3. ✅ Safety exemplaire (4.89/5, warnings pièges systématiques)
4. ✅ Intégration corpus v2 (Inserjeunes CFA visible, 3 phases ADR-039 équilibrées)
5. ✅ Système marque `(connaissance générale)` dans ~70% des cas sans source

### Points faibles (ordre de priorité S+1 / S+2)
1. 🔴 **Hallucinations stats précises avec sources plausibles** (précision 3.22/5)
   - Leviers : renforcer system prompt + fact-check LLM en aval
   - Potentiel gain : +0.5 à +1 pt précision
2. 🟡 **Retrieval mismatch sur queries à négation/inversion** (Q4, Q5, Q8, Q12)
   - Leviers : query rewrite, cross-encoder re-rank, enrichir fiche_to_text
   - Potentiel gain : +0.3 à +0.5 pt pertinence + précision
3. 🟡 **Personnalisation faible sur factuelles simples** (âge/scope du persona ignoré)
   - Leviers : consigne system prompt adaptation registre
   - Potentiel gain : +0.5 pt personnalisation sur 6 queries factuelles
4. 🟡 **Longueur non calibrée par type de query**
   - Leviers : consigne longueur par intent classifier
   - Potentiel gain : +0.3 pt verbosité

### Priorité pour INRIA J-31

Focalisation recommandée **précision factuelle** (le plus visible pour un jury) :
- Ajouter fact-check pass Haiku 4.5 en aval (coût ~$0.10/query × 100 queries = $10)
- Renforcer system prompt sur les stats : "ne JAMAIS citer un pourcentage sans source retrievée, marquer `(estimation, non vérifié)` si besoin"
- Enrichir `fiche_to_text()` pour exposer `insertion_pro.taux_emploi_*` dans les embeddings (actuellement non injecté) → les retrievals peuvent citer ces stats

Les autres leviers (retrieval, personnalisation, verbosité) restent S+1 post-soumission si temps.

---

**Artefacts** :
- 18 queries JSON : `results/bench_personas_2026-04-24/query_01_*.json` → `query_18_*.json`
- Résumé global : `results/bench_personas_2026-04-24/_ALL_QUERIES.json`
- Ce rapport : `results/bench_personas_2026-04-24/_SYNTHESIS.md`

**Temps moyen par query** : ~16s (retrieval + rerank + generate Mistral Medium).
**Total bench** : 18 queries × ~16s = ~5 min compute (+ 2 retries sur 429 rate limit).
**Coût Mistral estimé** : <$1 (inputs ~20k tokens × $0.40/M + outputs ~25k tokens × $1.20/M).
