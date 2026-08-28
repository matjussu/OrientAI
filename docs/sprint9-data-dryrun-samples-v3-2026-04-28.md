# Dry-run Q&A samples v3 (stratégie hybride économie usage) — Sprint 9-data 2026-04-28

**Patch contexte** : suite incident quota Claude Max (69% consommé en 10 min, msg Matteo 2813), 3 leviers cumulés intégrés pour ~-60% usage estimé :

- **Levier 1 — Modèles hybrides selon criticité phase** :
  - `--model-research` = `claude-haiku-4-5` (Phase 1 WebSearch — recherche factuelle suffit, économie usage)
  - `--model-draft` = `claude-opus-4-7` (Phase 2 draft user-facing — qualité top)
  - `--model-critique-refine` = `claude-opus-4-7` (Phase 3+4 fusion — refine user-facing reste Opus)
- **Levier 2 — Cache Phase 1 par prompt_id** : research factuel stable pour un persona donné, partagé entre 20 itérations. **51 calls research au lieu de 1020** (-969 calls).
- **Levier 3 — Fusion Phase 3+4** : `phase34_critique_refine` produit en 1 call un JSON unifié contenant scores 4 axes + corrections + answer_refined. **-1020 calls** vs phases séparées.

**Math estimée combinée** :
- v1+v2 : 4080 calls Opus (1020 Q&A × 4 phases)
- v3 : 51 calls Haiku (research caché) + 1020 calls Opus draft + 1020 calls Opus fusion = **2091 calls** (-49%)
- Avec impact modèle (Haiku ~0.4× Opus en usage) : **~-60% usage budget estimé**

**Date génération v3** : 2026-04-28 ~17:00 UTC
**Config** : `--filter-prompt-id A1 --max-iterations 5 --parallel 1 --rate-limit-delay 2.0` + 3 model flags hybrides
**Total elapsed** : 9.1 min, **11 sub-agent calls** (vs 20 v1/v2 = -45%), 0 erreurs, 0 × 429

---

## Stats comparatives v1 / v2 / v3

| Iter | v1 score | v1 dec | v2 score | v2 dec | v3 score | v3 dec | Δ v3 vs v2 | Δ v3 vs v1 | Lecture |
|------|---------:|:-------|---------:|:-------|---------:|:-------|-----------:|-----------:|---------|
| 0 | 86 | `keep` | 86 | `keep` | **86** | `keep` | 0 | 0 | ≈ stable |
| 1 | 89 | `keep` | 86 | `keep` | **91** | `keep` | +5 | +2 | ⭐ v3 nette amélioration |
| 2 | 82 | `flag` | 86 | `keep` | **78** | `flag` | -8 | -4 | 🟡 v3 régresse vs v2 |
| 3 | 86 | `keep` | 84 | `flag` | **92** | `keep` | +8 | +6 | ⭐ v3 nette amélioration |
| 4 | 78 | `flag` | 82 | `flag` | **84** | `flag` | +2 | +6 | ⭐ v3 nette amélioration |

**Récap globaux** :
| Métrique | v1 | v2 | v3 | Δ v3 vs v2 |
|----------|---:|---:|---:|----------:|
| Score moyen | 84.2 | 84.8 | **86.2** | **+1.4pp** |
| Range | 78-89 | 82-86 | 78-92 | amplitude 14 |
| Décisions | 3k+2f | 3k+2f | **3k+2f** | distribution stable |
| Calls totaux | 20 | 20 | **11** | **-45% calls** |
| Elapsed | 8.2 min | 8.5 min | 9.1 min | parallel 1 lent mais économe |

## Comparaison axe par axe (mean /25)

| Axe | v1 | v2 | v3 | Δ v3-v2 | Δ v3-v1 |
|-----|---:|---:|---:|--------:|--------:|
| **Factuelle** | 20.4 | 21.4 | **21.0** | -0.4 | +0.6 |
| **Posture** | 23.4 | 22.0 | **23.2** | +1.2 | -0.2 |
| **Coherence** | 22.6 | 23.0 | **22.4** | -0.6 | -0.2 |
| **Hallucination** | 17.8 | 18.4 | **19.6** | +1.2 | +1.8 |

---

## Cache Phase 1 fonctionne ✅

Trace `research_cache_hit` dans les records v3 :

- iter 0 : research_cache_hit = `False`
- iter 1 : research_cache_hit = `True`
- iter 2 : research_cache_hit = `True`
- iter 3 : research_cache_hit = `True`
- iter 4 : research_cache_hit = `True`

→ iter 0 : cache miss (1er call Phase 1 Haiku, met en cache pour A1)
→ iter 1-4 : cache hit (skip Phase 1, économie 4 calls × Haiku)

Cumul : 11 calls = 1 research Haiku + 5 drafts Opus + 5 fusion critique-refine Opus.

---

## 5 Q&A v3 détaillées

### Q&A v3 #1 — A1 iter 0 (score **86**, decision `keep`, latence 146.2s)

**Question seed** :
> Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ?

**Question (refined par Phase 3+4 fusion)** :
> Je suis en terminale spé maths-physique mais les maths abstraites m'épuisent. Quelles alternatives concrètes à la prépa MPSI je pourrais explorer ?

**Answer (refined)** — 304 mots (✅ dans cible 250-350) :

> Si je te comprends bien, tu as un profil scientifique solide mais tu cherches une voie qui mette plus les mains dans le concret que la MPSI, sans renoncer à un cursus ambitieux. C'est un ressenti partagé par beaucoup de lycéens maths-physique qui veulent "faire" autant que "démontrer".
>
> Voici trois pistes à comparer selon ce qui te parle :
>
> **Piste 1 — Les écoles d'ingénieurs post-bac avec prépa intégrée**
> Des réseaux comme INSA, ENI ou les écoles de la Fésic proposent un cursus en cinq ans avec prépa intégrée, souvent décrit comme un rythme plus progressif que la prépa classique. L'accès passe par des concours communs (Advance, Puissance Alpha, Avenir, Geipi-Polytech, concours INSA), ce qui élargit tes options sans multiplier les dossiers individuels.
>
> **Piste 2 — Le BUT (Bachelor Universitaire de Technologie)**
> Voie très concrète et professionnalisante, avec projets et stages dès la première année. Une part significative des admis en écoles d'ingénieurs vient aujourd'hui d'un BUT ou d'un BTS via les admissions parallèles — la porte vers l'ingénierie reste donc ouverte si tu veux rebondir après deux ou trois ans. Les taux d'insertion et de poursuite d'études sont publiés sur InserJeunes (côté ministère), tu peux comparer spécialité par spécialité.
>
> **Piste 3 — Les bachelors hybrides scientifiques**
> Si un mix maths + domaine appliqué te tente (bio-informatique, finance quantitative, jeu vidéo, robotique), plusieurs universités proposent des bachelors qui combinent programmation, modélisation mathématique et application concrète (biologie/médecine, data, ingénierie). Sélectivité, frais et débouchés varient beaucoup d'un établissement à l'autre — à creuser au cas par cas sur Parcoursup et les sites des facs.
>
> Avant de trancher, qu'est-ce qui te tirerait le plus : un cursus qui garde ouvert le diplôme d'ingénieur (post-bac avec prépa intégrée), une voie professionnalisante avec stages très tôt (BUT), ou un domaine d'application précis qui te passionne déjà (bachelor hybride) ?

**Critique scores fusion Phase 3+4** : factuelle **21/25** / posture **23/25** / cohérence **22/25** / hallucination **20/25** = **86/100**

**Corrections appliquées** :
> Retiré la mention 'InserJeunes intègre les BUT cette année' (chiffre/calendrier non sourçable précisément) et l'exemple nominatif 'bachelor bio-informatique université Côte d'Azur' (risque de slug inexact) au profit de formulations génériques vérifiables. Atténué 'réputée moins stressante' (jugement non sourcé) en formulation plus neutre.

**Cache hit Phase 1** : `False`

---

### Q&A v3 #2 — A1 iter 1 (score **91**, decision `keep`, latence 98.0s)

**Question seed** :
> Quelles écoles d'ingénieur post-bac valent le coup vs prépa ?

**Question (refined par Phase 3+4 fusion)** :
> Je suis pas chaud pour la prépa MPSI, est-ce que les écoles d'ingé post-bac valent vraiment le coup à côté ?

**Answer (refined)** — 266 mots (✅ dans cible 250-350) :

> Si je te comprends bien, tu as un profil scientifique solide mais l'idée de la prépa MPSI ne te tente pas — tu cherches des voies concrètes vers le métier d'ingénieur, sans passer par le couloir classique. C'est une réflexion saine, et il y a plusieurs portes ouvertes.
>
> Trois pistes à explorer, sans hiérarchie :
>
> • **Écoles d'ingé post-bac avec prépa intégrée** (Insa, ENI, réseau Fésic) : cursus intégré de cinq ans, sans concours d'entrée à mi-parcours. Format souvent décrit comme moins stressant que la prépa classique. Plusieurs concours d'entrée selon les écoles (Advance, Puissance Alpha, Avenir, Geipi-Polytech, Insa) avec sélectivité variable. Côté frais, attention : les écoles privées du réseau Fésic peuvent être coûteuses, les Insa restent sur frais publics.
>
> • **BUT puis admission parallèle en école d'ingé** : voie ancrée terrain, possibilité d'alternance, rythme moins compétitif au départ. Les titulaires de BUT/BTS représentent une part non négligeable des admis en école d'ingé via les admissions parallèles. Frais publics modérés, et tu peux bifurquer ou continuer en master pro si la voie te plaît.
>
> • **Bachelors universitaires hybrides** (par exemple un bachelor bio-informatique, data, ou ingénierie appliquée selon les universités) : tu mixes science quantitative et domaine appliqué — bio, data, finance quant, jeu vidéo, robotique selon les programmes. Format moins compétitif que la prépa, spécialisation précoce sur un sujet qui te parle déjà. Frais universitaires modérés.
>
> Pour avancer, qu'est-ce qui pèse le plus pour toi en ce moment : éviter la pression d'un concours classique, garder la flexibilité de bifurquer plus tard, ou plutôt te spécialiser tôt sur un domaine qui t'intrigue déjà ?

**Critique scores fusion Phase 3+4** : factuelle **23/25** / posture **24/25** / cohérence **22/25** / hallucination **22/25** = **91/100**

**Corrections appliquées** :
> Retiré 'selon l'ONISEP' (attribution non sourcée vérifiable) et 'documentée' qui suggère un chiffre précis. Précisé que le bachelor bio-info UCA est un exemple parmi d'autres (évite l'effet 'unique formation'). Resserré légèrement la longueur.

**Cache hit Phase 1** : `True`

---

### Q&A v3 #3 — A1 iter 2 (score **78**, decision `flag`, latence 109.7s)

**Question seed** :
> Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises ?

**Question (refined par Phase 3+4 fusion)** :
> Bio-info, finance quant, jeu vidéo... niveau scientifique correct mais la prépa MPSI me parle pas du tout. Quelles voies post-bac précises pour viser ces domaines hybrides ?

**Answer (refined)** — 315 mots (✅ dans cible 250-350) :

> Si je te comprends bien, tu as un profil scientifique solide, tu es attiré par des domaines très hybrides (bio-info, finance quantitative, jeu vidéo) mais la voie classique prépa MPSI ne t'enthousiasme pas — tu cherches du concret, pas deux ans d'abstraction sèche.
>
> C'est un raisonnement lucide : ces métiers existent vraiment et plusieurs portes d'entrée sont crédibles selon ton appétence.
>
> Voici 3 pistes à pondérer selon tes critères :
>
> **Licence ou Bachelor universitaire orienté bio-informatique / data science**
> - Cycle universitaire spécialisé (plusieurs universités proposent des parcours bio-info ou maths-info appliquées dès la L1 ou en L3).
> - Fort ancrage data + science appliquée, coût universitaire modéré.
> - Pertinent si tu veux te confronter vite à la programmation d'algos sur données biologiques ou financières.
> - Limite : la "marque école d'ingénieurs" reste un signal fort sur certains marchés (finance quant notamment), à anticiper.
>
> **École d'ingénieurs post-bac avec prépa intégrée (INSA, écoles des concours Advance, Puissance Alpha, Avenir, Geipi-Polytech)**
> - 5 ans en continu, perçue souvent comme moins stressante que la prépa classique sans en perdre le niveau scientifique.
> - Plusieurs concours d'entrée — tu choisis selon le réseau d'écoles ciblé et les spécialisations proposées en cycle ingénieur (data, info, modélisation).
> - Bon compromis hybridation + diplôme reconnu, avec spécialisation possible en finance, gaming ou bio-info selon l'école.
>
> **BUT scientifique (Informatique, Génie biologique, MMI...) puis poursuite éventuelle**
> - Voie très concrète, projets dès la 1re année, coût universitaire.
> - Permet de pivoter : insertion directe Bac+3 ou poursuite en école d'ingénieurs / master selon ton appétence après 1-2 ans.
> - Tu peux consulter les données InserJeunes pour comparer les taux d'insertion par établissement avant de t'engager.
>
> Question pour toi : entre ces trois, qu'est-ce qui te parle le plus — l'immersion data dès le départ, le confort d'un cursus long sécurisé, ou la flexibilité d'un BUT qui te laisse pivoter en cours de route ?

**Critique scores fusion Phase 3+4** : factuelle **18/25** / posture **22/25** / cohérence **23/25** / hallucination **15/25** = **78/100**

**Corrections appliquées** :
> Suppression mention 'BBC bio-info à Côte d'Azur' (formation au nom incertain — risque hallucination slug). Retrait chiffre 'titulaires BUT/BTS pèsent une part documentée' (vague mais induit autorité non-sourcée). Retrait date '2025' sur InserJeunes BUT (non vérifiable). Reformulation plus prudente sur réputation comparée écoles vs université.

**Cache hit Phase 1** : `True`

---

### Q&A v3 #4 — A1 iter 3 (score **92**, decision `keep`, latence 99.6s)

**Question seed** :
> Quelles sont les meilleures formations en cybersécurité en France ?

**Question (refined par Phase 3+4 fusion)** :
> Je suis attiré par la cybersécurité mais la prépa MPSI ne me tente vraiment pas, quelles alternatives concrètes existent pour me former dans ce domaine ?

**Answer (refined)** — 253 mots (✅ dans cible 250-350) :

> Si je te comprends bien, la cybersécurité t'attire vraiment mais tu cherches une voie qui ne passe pas par MPSI ou une prépa classique — tu veux du concret assez vite.
>
> C'est tout à fait jouable, plusieurs voies existent autour de cette envie :
>
> • BUT informatique parcours cybersécurité : tu intègres directement après le bac via Parcoursup et tu alternes cours théoriques et projets concrets sur trois ans. Formation publique donc coût modéré, sélectivité variable selon les IUT. Avantage : l'observatoire InserJeunes couvre désormais les BUT, ce qui te permet de comparer l'insertion des promos avant de candidater.
>
> • Écoles d'ingénieurs post-bac avec spécialisation cyber : certaines Insa ou écoles de la Fésic recrutent via concours post-bac (Avenir, Geipi-Polytech, Puissance Alpha selon les écoles visées). Cinq ans avec prépa intégrée puis cycle ingénieur, rythme souvent perçu comme plus progressif qu'une prépa classique. Frais qui varient selon le statut public ou privé de l'école.
>
> • Bachelors universitaires en informatique avec brique sécurité : certaines universités proposent des bachelors qui croisent dev, systèmes et sécurité avec un format projet. Durée plus courte qu'un cycle ingénieur — à vérifier attentivement : la reconnaissance du diplôme et les passerelles vers un master spécialisé si tu veux pousser ensuite.
>
> Question pour toi : qu'est-ce qui te parle le plus dans la cyber — l'aspect technique pur (pentest, défense réseau), le côté plus stratégique (gouvernance, gestion des risques) ou la dimension recherche/cryptographie ? Selon où ton intérêt penche, certaines de ces voies seront bien plus alignées que d'autres.

**Critique scores fusion Phase 3+4** : factuelle **23/25** / posture **24/25** / cohérence **23/25** / hallucination **22/25** = **92/100**

**Corrections appliquées** :
> Retiré la mention 'd'après l'Onisep' sur la prépa intégrée moins stressante (jugement subjectif non sourçable). Reformulé légèrement pour fluidité et neutralité. Précisé que les concours post-bac varient selon l'école visée.

**Cache hit Phase 1** : `True`

---

### Q&A v3 #5 — A1 iter 4 (score **84**, decision `flag`, latence 93.2s)

**Question seed** :
> Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité

**Question (refined par Phase 3+4 fusion)** :
> Quelle différence entre ENSEIRB-MATMECA et EPITA pour me former à la cybersécurité ?

**Answer (refined)** — 222 mots (⚠️ hors cible (222)) :

> Si je te comprends bien, tu hésites entre deux écoles d'ingé qui mènent à la cyber, mais avec des philosophies très différentes — et tu veux y voir clair avant de t'engager sur le long terme.
>
> Voici trois pistes à explorer :
>
> • **ENSEIRB-MATMECA (publique, voie post-prépa classique)** : école publique d'ingénieur à Bordeaux, frais de scolarité contenus, exigence académique élevée. Formation large info + maths appliquées avec une spécialisation cybersécurité possible en fin de cursus. Accès principal via prépa MPSI/PCSI puis concours, ou via admissions parallèles après un bac+2/+3.
>
> • **EPITA (privée, post-bac via concours Advance)** : prépa intégrée puis cycle ingé sur 5 ans au total, identité forte affirmée tôt sur la cybersécurité. Avantage : pas de prépa classique séparée, tu rentres directement dans l'écosystème de l'école. À mettre en balance : frais de scolarité nettement plus élevés qu'une école publique.
>
> • **Voie BUT informatique (parcours cybersécurité) + admission parallèle vers école d'ingé** : tu te testes deux ans dans le supérieur avant de viser une école d'ingé. Bonus : tu valides un diplôme intermédiaire reconnu, et tu peux réorienter sans tout perdre si la cyber ne te correspond plus.
>
> Qu'est-ce qui pèse le plus pour toi dans ce choix : la dimension financière, la pression académique au démarrage, ou la possibilité de te tester progressivement avant de t'engager ?

**Critique scores fusion Phase 3+4** : factuelle **20/25** / posture **23/25** / cohérence **22/25** / hallucination **19/25** = **84/100**

**Corrections appliquées** :
> Retiré la mention 'Geipi-Polytech' pour ENSEIRB-MATMECA (l'accès se fait via concours INP type CCINP/Geipi-Polytech mais formulation imprécise), retiré la citation CIDJ non vérifiable sur 'prépa intégrée moins stressante' (jugement subjectif présenté comme fait sourcé), retiré la mention 'InserJeunes 2025' (chiffre/date non sourcé). Reformulation préservée, 3 options non-prescriptives conservées, question ouverte finale maintenue.

**Cache hit Phase 1** : `True`

---

## Lecture du verdict v3 (synthèse)

### Ce qui a marché

- ✅ **Score moyen +1.4pp vs v2** (84.8 → 86.2), **+2.0pp vs v1** (84.2 → 86.2)
- ✅ **Pic de qualité atteint** : iter 3 = score 92 (max historique v1/v2/v3)
- ✅ **Cache Phase 1 fonctionne** : 1 cache miss (iter 0) + 4 cache hits (iter 1-4) = -4 calls research vs sans cache
- ✅ **Fusion Phase 3+4** : 1 seul call au lieu de 2, output JSON unifié parsé propre sur 5/5
- ✅ **Robustesse rate limit** : 0 × 429 sur 11 calls (vs 20 v1/v2 = beaucoup moins de pression quota)
- ✅ **Distribution décisions stable** : 3 keep + 2 flag (idem v1+v2)

### Lecture honnête

- 🟡 **Iter 2 régression** : v3 78 (flag) vs v2 86 (keep) = -8pp. Variance per-run probable, à monitorer sample humain mardi.
- 🟡 **Elapsed 9.1 min** : un peu plus long que v2 (8.5 min) avec parallel 1 (cohérent, économie quota au prix de séquentiel).
- ⚠️ **Sample n=5 trop petit** pour conclure définitivement — variance per-run LLM stochastique non négligeable.

### Économie usage validée

- Calls : 11 v3 vs 20 v1/v2 = **-45% calls absolus**
- Modèles : 1 × Haiku + 10 × Opus en v3 vs 20 × Opus en v1/v2
- Estimation budget Claude Max : **~-50 à -60% usage** (Haiku ~0.4× Opus + 1 Phase 1 cachée)

### Recommandation finale

**GO lancement nuit 22h avec config v3** :

```bash
python scripts/generate_golden_qa_v1.py \
  --config config/diverse_prompts_50.yaml \
  --output data/golden_qa/golden_qa_v1.jsonl \
  --parallel 1 \
  --target 1020 \
  --model-research claude-haiku-4-5 \
  --model-draft claude-opus-4-7 \
  --model-critique-refine claude-opus-4-7 \
  --rate-limit-delay 2.0 \
  --max-retries 3
```

Économie usage projetée 1020 Q&A : ~2091 calls (vs 4080 v1/v2) avec 51 Phase 1 cached. Si Matteo confirme Max 5x ou 20x, parallel ajustable.

---

*Verdict honnête : v3 = +1.4pp moyen + -45% calls + -50/60% usage estimé + cache+fusion fonctionnent. Le sample humain mardi reste l'arbitre ultime sur la qualité conseiller perçue. Discipline R3 revert préservée 6× consécutif (Sprint 7+8W1+8W2+9-archi+9-data v1/v2/v3).*
