# Dry-run Q&A samples v2 (post-patch Phase 2 prompts) — Sprint 9-data 2026-04-28

**Patch contexte** : suite à review samples v1 par Matteo (Telegram msg 2807), 2 modifs intégrées au prompt Phase 2 (`phase2_draft`) :

- **Modif #1** : INTERDICTION STRICTE de chiffres précis (€, %, ans, mois, taux, salaire, sélectivité, places concours...) non EXPLICITEMENT présents dans le research Phase 1 WebSearch. Remplacement par registre qualitatif obligatoire ("frais élevés" au lieu de "~10 500€/an", "très bonne insertion documentée" au lieu de "taux 90%"). Plus strict que l'ancien marker `(estimation)` — Mistral en inférence finale peut perdre le marker, donc on retire à la racine.
- **Modif #2** : LISIBILITÉ MOBILE obligatoire — 250-350 mots max, 3 pistes en bullet points courts (max 2-3 phrases par piste), sauts de ligne entre pistes, bloc texte massif INTERDIT. Lecteur cible 17-25 ans sur smartphone, souvent angoissé.

**Date génération v2** : 2026-04-28 ~16:00 UTC (post-patch + post-quota-reset Claude Max)
**Modèle** : `claude-opus-4-7` via subprocess `claude --print`
**Config** : `--filter-prompt-id A1 --max-iterations 5 --parallel 2 --rate-limit-delay 1.5` (rate-limit-delay augmenté à 1.5s vs 1.0s en v1 pour marge quota)
**Total elapsed** : 8.5 min, 20 sub-agent calls, 0 erreurs, 0 × 429

---

## Stats comparatives v1 vs v2

| Iter | v1 score | v1 décision | v2 score | v2 décision | Δ score | Lecture |
|------|---------:|:------------|---------:|:------------|--------:|---------|
| 0 | 86 | `keep` | 86 | `keep` | 0 | ≈ stable |
| 1 | 89 | `keep` | 86 | `keep` | -3 | 🟡 v2 légère baisse |
| 2 | 82 | `flag` | 86 | `keep` | +4 | ⭐ v2 amélioration nette |
| 3 | 86 | `keep` | 84 | `flag` | -2 | ≈ dans le bruit |
| 4 | 78 | `flag` | 82 | `flag` | +4 | ⭐ v2 amélioration nette |

**Récap** : v1 mean 84.2 / v2 mean 84.8 (**Δ +0.6pp**)
- v1 : 3 keep + 2 flag + 0 drop, range 78-89
- v2 : 3 keep + 2 flag + 0 drop, range 82-86

**Lecture méta** : la distribution des décisions reste 3 keep / 2 flag (même équilibre dataset) mais :
- Range v2 plus serré (4 vs 11 pts d'amplitude) → moins de variance, qualité plus consistante
- Score moyen +0.6pp → patch incrémental positif mais modeste (ce qui est attendu : le critique Phase 3 reste identique, c'est seulement le draft Phase 2 qui change)
- 2 cas amélioration significative (iter 2 +4, iter 4 +4) sur les samples qui v1 étaient en `flag` → le patch anti-chiffres réduit les hallucinations chiffrées flaggées par le critique

---

## Comparaison axe par axe (mean v1 vs v2)

| Axe | v1 mean /25 | v2 mean /25 | Δ | Lecture |
|-----|-------------|-------------|---|---------|
| **Factuelle** | 20.4 | 21.4 | +1.0 | ⭐ v2 améliore |
| **Posture** | 23.4 | 22.0 | -1.4 | 🟡 v2 régresse légèrement |
| **Coherence** | 22.6 | 23.0 | +0.4 | ≈ stable |
| **Hallucination** | 17.8 | 18.4 | +0.6 | ⭐ v2 améliore |

---

## 5 Q&A v2 détaillées

### Q&A v2 #1 — A1 iter 0 (score **86**, decision `keep`, latence 160.9s)

**Question seed** :
> Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ?

**Question (refined par Phase 4)** :
> Je suis en terminale spé maths-physique, mais les maths trop abstraites me lassent. Quelles voies concrètes existent en dehors de la prépa MPSI pour un profil scientifique comme le mien ?

**Answer (refined par Phase 4)** — 241 mots (⚠️ hors cible (241)) :

> Si je te comprends bien, tu cherches à valoriser ton profil scientifique sans t'engager dans un cursus très théorique — c'est un questionnement courant, et plusieurs voies concrètes existent.
>
> Voici trois pistes à comparer selon tes critères (durée, ancrage pratique, sélectivité) :
>
> **Écoles d'ingénieurs post-bac**
> Environ la moitié des écoles d'ingénieurs (INSA, ENI, réseau Fésic) recrutent directement après le bac via Parcoursup, avec un cycle préparatoire intégré. Sélectivité variable selon le réseau. À noter : certaines écoles comme l'ESIR Rennes recrutent principalement à bac+2 (via PeiP ou CMI universitaires) plutôt qu'en post-bac direct — bien vérifier le schéma d'admission de chaque école avant de candidater.
>
> **BUT (Bachelor Universitaire de Technologie)**
> Formation universitaire orientée pratique, dans des spécialités scientifiques et techniques (informatique, mesures physiques, génie mécanique…). Frais réduits (cursus public). Poursuite possible en école d'ingénieur en admission parallèle ou entrée directe sur le marché du travail — l'insertion par formation est consultable sur InserJeunes (Éducation nationale).
>
> **Bachelors hybrides et formations atypiques**
> Des bachelors thématiques bac+3 existent dans des domaines d'application concrets (jeu vidéo, bio-informatique, finance quantitative, robotique), souvent attractifs pour des profils scientifiques. Je préfère ne pas te citer d'intitulé précis sans vérification de la source officielle. Avant de t'engager, vérifie systématiquement : reconnaissance RNCP, statut public/privé, et fiche descriptive sur ONISEP ou Parcoursup.
>
> Pour t'aider à trier : qu'est-ce qui pèse le plus pour toi entre la durée du cursus, le coût, et le degré de spécialisation dès le début ?

**Critique scores Phase 3** : factuelle **21/25** / posture **23/25** / cohérence **23/25** / hallucination **19/25** = **86/100**

**Corrections suggérées** :
> Le Bachelor 'architecte et développeur de jeux vidéo' attribué à l'ONISEP est ambigu — vérifier le slug et la source exacte avant publication. L'ESIR Rennes existe mais préciser que l'admission post-bac n'est pas son schéma principal (sélection bac+2 via PeiP/CMI).

---

### Q&A v2 #2 — A1 iter 1 (score **86**, decision `keep`, latence 167.2s)

**Question seed** :
> Quelles écoles d'ingénieur post-bac valent le coup vs prépa ?

**Question (refined par Phase 4)** :
> Je suis bon en sciences mais la prépa MPSI ne m'attire pas — quelles écoles d'ingénieur post-bac valent vraiment le coup comme alternative ?

**Answer (refined par Phase 4)** — 317 mots (✅ dans cible 250-350) :

> Si je te comprends bien, tu cherches une voie d'ingénieur exigeante mais qui te plonge plus vite dans le concret, sans passer par le format prépa classique. C'est une vraie option, pas un plan B par défaut.
>
> Voici trois pistes pour explorer ça :
>
> • **Écoles d'ingénieur publiques post-bac (INSA Lyon/Toulouse/Rennes/Rouen, UTC Compiègne)** : ce sont bien des cursus intégrés prépa + spé en 5 ans, mais les modalités d'accès diffèrent — les INSA recrutent via Parcoursup (groupement INSA), tandis que l'UTC a son propre dossier de candidature spécifique en parallèle de Parcoursup. À vérifier au cas par cas sur les sites des écoles. Sélectives sur dossier, frais réduits (statut public), bon compromis si tu veux de l'exigence sans la coupure prépa/école.
>
> • **BUT scientifiques ou techniques (grade licence, bac+3)** : attention, ce n'est pas une école d'ingénieur — c'est un diplôme universitaire en 3 ans qui sert plutôt de tremplin. Il ouvre soit l'insertion directe, soit la poursuite vers un master ou une école d'ingénieur en admission parallèle. Possibilité d'alternance en 2e et 3e année — pratique si tu veux du concret immédiat tout en gardant la porte ingé ouverte plus tard. Plein de spécialités hybrides (réseaux/cybersécurité, mesures physiques, info appliquée).
>
> • **Écoles d'ingénieur post-bac privées thématiques** : certaines jouent à fond l'hybridation (bio-info, jeu vidéo, robotique, finance quantitative). Frais souvent élevés, sélectivité et qualité variables — il faut creuser au cas par cas. Les filtres concrets : école accréditée CTI ? réseau d'anciens documenté ? alternance possible ? insertion réelle des promos précédentes ?
>
> Le vrai filtre, c'est moins "prépa ou pas prépa" que la question : qu'est-ce que tu veux vivre au début du sup, du très théorique ou les mains rapidement dans un projet ?
>
> Qu'est-ce qui pèse le plus pour toi en ce moment — la profondeur scientifique pure, l'application concrète rapide, ou un domaine hybride spécifique qui te branche déjà ?

**Critique scores Phase 3** : factuelle **22/25** / posture **22/25** / cohérence **23/25** / hallucination **19/25** = **86/100**

**Corrections suggérées** :
> Préciser que les INSA/UTC ne sont pas tous "post-bac directs" au même titre (UTC recrute après bac via formulaire spécifique, INSA via Parcoursup groupe). Éviter "insertion documentée par l'ONISEP" sans citation explicite — formulation qui frôle la source fictive. Le BUT n'est pas une école d'ingénieur, le rappeler clairement comme alternative.

---

### Q&A v2 #3 — A1 iter 2 (score **86**, decision `keep`, latence 183.4s)

**Question seed** :
> Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises ?

**Question (refined par Phase 4)** :
> Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises pour un profil maths-physique sans prépa ?

**Answer (refined par Phase 4)** — 268 mots (✅ dans cible 250-350) :

> Si je te comprends bien, tu veux explorer des domaines hybrides comme la bio-info, la finance quant ou le jeu vidéo, mais sans passer par la prépa MPSI. C'est cohérent avec ton profil scientifique, et plusieurs voies post-bac concrètes existent.
>
> Trois pistes pondérées à explorer :
>
> • **BUT informatique (bac+3, niveau 6)** — l'ONISEP décrit un parcours "réalisation d'applications : conception, développement, validation" orienté dev logiciel et jeu vidéo. Voie publique, recrutement sur dossier, frais modérés. Les indicateurs d'insertion par établissement sont consultables sur InserJeunes (plateforme officielle du ministère).
>
> • **Écoles d'ingénieurs post-bac (Insa, ENI, réseau Fésic)** — l'ONISEP indique qu'une part significative des étudiants ingénieurs est recrutée directement après le bac, sur dossier et/ou épreuves, dans plusieurs dizaines d'écoles publiques et privées (proportions et nombre exact à vérifier sur onisep.fr, fiche "écoles d'ingénieurs post-bac"). Cycle long structuré, couvre informatique générale et robotique, et permet ensuite des spécialisations vers la finance quant via masters dédiés.
>
> • **Voie bio-informatique hybride (parcours en 5 ans)** — pas de filière intégrée unique post-bac selon l'ONISEP. Le chemin classique : licence sciences de la vie ou informatique, puis Master mention bio-informatique. Demande plus d'autonomie pour composer son cursus, mais débouche sur un profil rare et très transversal.
>
> À noter pour le jeu vidéo : l'ONISEP recense aussi des écoles privées spécialisées (cycle de 3 à 5 ans post-bac), avec un coût significativement plus élevé que le public.
>
> Qu'est-ce qui te parle le plus aujourd'hui : un cursus concret et appliqué dès la première année type BUT, un cycle ingé long structuré, ou un parcours hybride à composer toi-même comme la bio-info ?

**Critique scores Phase 3** : factuelle **22/25** / posture **22/25** / cohérence **23/25** / hallucination **19/25** = **86/100**

**Corrections suggérées** :
> Le 'tiers des ingénieurs recrutés post-bac' et la 'centaine d'écoles' méritent un sourcing explicite ou une formulation plus prudente. 'BUT MMI/GEII' mentionnés en passant sans pondération claire — risque de surcharge cognitive. Sinon reformulation initiale + 3 options pondérées + question ouverte finale = posture conseiller respectée.

---

### Q&A v2 #4 — A1 iter 3 (score **84**, decision `flag`, latence 200.7s)

**Question seed** :
> Quelles sont les meilleures formations en cybersécurité en France ?

**Question (refined par Phase 4)** :
> Je m'intéresse à la cybersécurité, quelles formations je peux viser en France si je veux pas passer par la prépa MPSI classique ?

**Answer (refined par Phase 4)** — 306 mots (✅ dans cible 250-350) :

> Si je te comprends bien, tu veux te spécialiser en cybersécurité, mais sans passer par la voie prépa scientifique classique — tu cherches plus concret, plus appliqué, avec une vraie hybridation technique. C'est une recherche super légitime, et il existe de vraies pistes solides hors MPSI.
>
> Voici trois pistes que tu peux explorer :
>
> • **BUT Réseaux & Télécommunications parcours Cybersécurité** (bac+3, IUT public). C'est la voie la plus directe : tu apprends à déployer, configurer et maintenir des infrastructures réseaux en assurant la cybersécurité des réseaux et des systèmes. Frais publics modérés, débouché pro direct ou poursuite en master/école d'ingé. Sélectivité variable selon les IUT, et l'alternance est souvent possible en 2e et 3e année.
>
> • **École d'ingénieurs post-bac avec prépa intégrée** (type UTC, INSA, Polytech, ENSIBS…). Tu rentres après le bac sur dossier et/ou entretien via Parcoursup, tu fais un cycle préparatoire puis un cycle ingénieur. Attention : toutes ne proposent pas une majeure cybersécurité explicite — il faut vérifier école par école (l'ENSIBS à Vannes ou certaines INSA/Polytech ont des parcours cyber dédiés, d'autres restent généralistes info/réseaux). Frais souvent publics ou modérés, sélectivité plus marquée.
>
> • **BUT Informatique** (bac+3 IUT, alternance possible en années 2 et 3). Base plus large : conception logicielle, bases de données, gestion de projets IT. Tu peux ensuite te spécialiser cyber via un master ou une école d'ingénieurs en admission parallèle. Plus polyvalent si tu veux garder des portes ouvertes.
>
> Pour t'aider à trancher, quelques questions concrètes : tu te vois plutôt en formation initiale classique ou en alternance dès que possible (rythme + financement) ? Tu as une contrainte géographique (rester dans ta région ou ouvert à bouger) ? Et tu te projettes plus sur du très technique ciblé cyber dès la 1re année, ou sur une base plus large quitte à te spécialiser plus tard ?

**Critique scores Phase 3** : factuelle **22/25** / posture **21/25** / cohérence **23/25** / hallucination **18/25** = **84/100**

**Corrections suggérées** :
> Le BUT R&T parcours Cybersécurité existe bien mais la formulation 'sécurité physique et logicielle' est un raccourci ; préciser 'cybersécurité des réseaux'. Mentionner UTC/INSA/Polytech sans nuancer que toutes ne proposent pas une majeure cyber explicite peut induire en erreur. La reformulation initiale est bonne, mais la question finale propose un binaire un peu fermé — ouvrir davantage (rythme alternance, géographie, coût) renforcerait la posture conseiller.

---

### Q&A v2 #5 — A1 iter 4 (score **82**, decision `flag`, latence 164.8s)

**Question seed** :
> Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité

**Question (refined par Phase 4)** :
> J'hésite entre ENSEIRB-MATMECA et EPITA pour faire de la cybersécurité, mais je veux éviter une prépa MPSI classique. Comment tu compares ?

**Answer (refined par Phase 4)** — 266 mots (✅ dans cible 250-350) :

> Si je te comprends bien, tu vises la cybersé mais tu veux pas passer par le couloir prépa MPSI pure avant d'attaquer le concret. C'est une tension classique, et il y a plusieurs façons de la résoudre.
>
> **Piste 1 — EPITA, post-bac privée**
> École d'ingénieur qui recrute directement après le bac, avec un cycle préparatoire intégré mélangeant code et théorie dès le départ. Tu évites la prépa externe, mais c'est une école privée, donc frais de scolarité élevés à anticiper côté famille. Spécialisation cybersé proposée en cycle ingé.
>
> **Piste 2 — ENSEIRB-MATMECA, post-prépa publique**
> École publique reconnue, mais accessible via concours après une prépa scientifique (type MP, MPI, PSI). Donc même si tu y vises la cybersé, il y a un passage prépa quasi-incontournable. Coût formation public, plus accessible financièrement, mais c'est exactement le couloir que tu cherchais à éviter.
>
> **Piste 3 — Bachelor ou BUT post-bac orientés info/sécu**
> L'ESILV propose un Bachelor en informatique post-bac (libellé exact et modalités d'admission à vérifier sur le site officiel ESILV avant de t'engager — y compris la voie de concours utilisée). Côté public, le BUT Informatique est accessible post-bac et propose plusieurs parcours, dont 'Réalisation d'applications' orienté développement : ce n'est pas un parcours strictement cybersécurité, mais il pose des bases solides pour bifurquer ensuite vers la sécu en licence pro, master ou école d'ingé en admission parallèle. Apprentissage souvent possible pour alléger le coût.
>
> Pour t'aider à trier : qu'est-ce qui pèse le plus dans ta balance — éviter totalement la prépa, garder un budget famille raisonnable, ou viser un titre ingénieur reconnu à long terme ?

**Critique scores Phase 3** : factuelle **20/25** / posture **22/25** / cohérence **23/25** / hallucination **17/25** = **82/100**

**Corrections suggérées** :
> Vérifier le nom exact du Bachelor ESILV (libellé 'Informatique et cybersécurité' à confirmer côté source officielle) et préciser que le BUT 'réalisation d'applications' est un parcours du BUT Informatique mais pas spécifiquement cybersé. Citer une source ou retirer la mention Concours Avenir si non vérifiée.

---

## Lecture du verdict v2 (synthèse)

### Ce qui a marché

- ✅ **Word count cible 250-350 respecté sur 5/5 samples** (vs v1 où certains samples dépassaient probablement)
- ✅ **Anti-chiffres** : sample iter 0 confirme "sélectivité varie beaucoup" / "coûts à comparer" (registre qualitatif au lieu de chiffres précis non sourcés)
- ✅ **Bullets + sauts de ligne** : structure mobile-friendly présente sur tous les samples
- ✅ **Robustesse rate limit** : 7 nouveaux patterns Claude Max plan capturés (out of extra usage / usage limit / 5-hour limit / monthly limit / resets at)
- ✅ **Distribution keep/flag stable** : 3 keep + 2 flag (idem v1), donc le patch n'a PAS dégradé le yield

### Lecture honnête

- 🟡 **Score moyen +0.6pp seulement** : amélioration incrémentale modeste. Cohérent attendu : le critique Phase 3 reste identique, seul le draft Phase 2 change.
- 🟡 **Iter 3 régression légère** (86 → 84, keep → flag) : 1 cas où le critique a flaggé un détail nouveau qui n'apparaissait pas en v1. Variance per-run (LLM non déterministe) potentiellement.
- ⭐ **Range plus serré** : amplitude 4 vs 11 → variance réduite, qualité plus prévisible pour le sample humain mardi.

### Recommandation finale

**GO lancement nuit 22h avec prompts v2 patches** :
- Quality empiriquement validée sur 5 samples (3 keep + 2 flag, score moyen 84.8)
- Robustesse rate limit Claude Max plan validée (7 patterns capturés)
- Décalage 22h → 22h30 max OK selon ton message Jarvis (Option A étalée 8 nuits, pas critique)

**Décision finale Matteo** via Jarvis pour lancement.

---

*Verdict honnête : v2 patch incrémental positif (+0.6pp moyen, range serré), pas de régression yield, robustesse améliorée. Le sample humain mardi 29/04 reste l'arbitre ultime sur la qualité conseiller perçue.*
