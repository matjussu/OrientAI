# L3 - Audit du pipeline data (corpus réel)

Ordre : 2026-06-09-1030-claudette-orientai-audit-empirique
Auteur : Claudette
Date : 2026-06-09
Méthode : mesure directe sur `data/processed/formations.json` (le corpus réellement servi en prod, cf `server.py` `ORIENTIA_FICHES_PATH`). Aucune confiance à la doc : tout est compté par `data_audit.py`. Artefact brut : `results/data_audit.json`.

---

## 0. Pourquoi ce volet est le suspect n°1

L'état de l'art 2026 et les observations empiriques convergent : quand un RAG échoue, c'est le retrieval/la data ~73 % du temps, pas la génération. La batterie L1 le confirme (sur-refus, substitution de métrique, "réponse à côté" dominent l'hallucination franche). Or la data d'OrientAI a été collectée et transformée maison : c'est précisément là qu'il faut regarder. Ce volet mesure ce que le corpus contient vraiment.

---

## 1. Volume et diversité des sources (point fort réel)

- **47 220 fiches** au total, **43 185 retrieval-eligible** (91,5 %).
- **25 sources** agrégées. Aucune ne dépasse 17,3 % du corpus (Parcoursup 8 191). La diversité institutionnelle annoncée dans le dossier est réelle et vérifiée : pas de source unique dominante qui imposerait son biais.

Divergence doc/réel n°1 : la doc interne du repo (`CLAUDE.md`) annonce "443 fiches (343 Parcoursup + 102 ONISEP)". Le corpus réel en compte 47 220. La doc est obsolète d'un facteur ~100. Confirme la consigne de Matteo : ne pas fonder un diagnostic sur la doc.

Top sources mesurées : parcoursup 8191, monmaster 7573, rncp 5181, rncp_blocs 4891, onisep 4758, inserjeunes_cfa 4065, labonnealternance 4008, inserjeunes_lycee_pro 2693, rome 1584, dares 1160, onisep_ideo 1075, onisep_metiers 1075, insersup 368, ip_doc 240, insee_salaires 59, crous 45, financement 28, domtom_curated 16, apec 13, calendriers 21.

---

## 2. Couverture géographique : le trou structurel

| Mesure | Valeur | Commentaire |
|---|---|---|
| Région présente (sur 43 185 eligible) | 23 380 (54,1 %) | |
| **Région absente** | **19 805 (45,9 %)** | quasi la moitié du corpus sans région |
| `ville` clé présente | 33 794 | |
| `ville` réellement non-vide | 15 782 | |
| **`ville` = chaîne vide** | **18 012** | piège : "présent" mais inutilisable |

Divergence doc/réel n°2 : la doc/le premier audit citaient "41,5 % de région manquante". La mesure réelle donne **45,9 %**. La situation est pire que documentée.

Finding majeur (piège de la chaîne vide) : 18 012 fiches ont un champ `ville` présent mais égal à `""`. Un filtre géographique naïf qui teste "ville présente" les considère comme localisées alors qu'elles ne le sont pas. C'est exactement le type de défaut qui fait échouer silencieusement les requêtes géo (cf L1 edge_geo : réponses qui sur-élargissent ou ratent la contrainte régionale).

DOM-TOM : 813 fiches eligible taguées d'une région d'outre-mer (La Réunion 408, Guadeloupe 176, Guyane 103, Martinique 102, Mayotte 24). C'est nettement plus que les "16 fiches DOM-TOM" évoquées (divergence doc/réel n°3) - mais cette couverture vient du tagging régional, pas d'une intégration ciblée, et la profondeur (chiffres d'admission/insertion sur ces fiches) reste à vérifier cas par cas.

---

## 3. Champs chiffrés : le coeur du refus honnête

Le refus honnête ("pas de chiffre = pas d'invention") ne fonctionne que si les chiffres vivent dans des champs typés avec `null` explicite. C'est bien le design (point fort). Mais la COUVERTURE de ces chiffres est faible, ce qui explique le taux de refus élevé observé en L1 :

| Champ chiffré | Présent non-null | % du corpus |
|---|---|---|
| `taux_acces_parcoursup_2025` | 8 191 | **17,3 %** |
| `nombre_places` | 8 191 | 17,3 % |
| `insertion_pro.taux_emploi_6m` | 13 347 | 28,3 % |
| `insertion_pro.part_emploi_6m` | 2 259 | 4,8 % |
| `insertion_pro.part_poursuite_etudes` | 2 259 | 4,8 % |
| champ `debouches` structuré | 2 468 | 5,2 % |

Lecture : le taux d'accès Parcoursup n'existe que pour **17 % des formations** (le sous-ensemble Parcoursup). Pour les 83 % restantes, il n'y a structurellement aucun taux d'accès. De même, les débouchés structurés ne couvrent que 5 % du corpus. Conséquence directe et mesurée en L1 : sur une question d'insertion ou de débouché, le système n'a très souvent rien à citer, donc il refuse, et parfois substitue une autre métrique (le taux d'accès, qui lui est plus présent).

Piège present-but-empty : sur les 14 771 fiches qui ont un bloc `insertion_pro`, **1 098 (7,4 %) ont TOUS les champs à null**. Le bloc existe mais ne porte aucune donnée. Si le code teste "bloc insertion présent" plutôt que "valeur non-null", il croit avoir l'info qu'il n'a pas.

---

## 4. Fraîcheur : hétérogène, et structurellement lagged

Le dossier vend "données fraîches, refresh mensuel" comme avantage sur un LLM à connaissance figée. C'est vrai pour les calendriers et une partie de Parcoursup, mais la mesure nuance fortement pour les stats d'insertion :

Distribution des années (champ `annee`) : `cumul 2023-2024` (1384), `cumul 2022-2023` (790), `cumul 2021-2022` (627), `cumul 2018-2019` (575), `cumul 2020-2021` (427), `cumul 2019-2020` (262), puis 2024 (188), 2025 (77), 2026 (32), 2018 (1)...

Lecture : les statistiques d'insertion sont par nature retardées (cumuls pluriannuels jusqu'à `2018-2019`). Ce n'est pas un défaut d'OrientAI (les sources publiques elles-mêmes sont laggées), mais c'est une nuance à assumer : "données fraîches" s'applique aux échéances et aux taux d'accès de la dernière campagne, pas aux insertions, qui ont 2 à 7 ans de retard. À ne pas survendre.

---

## 5. Séparation structuré / texte

Bon design vérifié : les chiffres vivent dans des champs typés (`taux_acces_parcoursup_2025`, `insertion_pro.*`), pas dans du texte libre, avec `null` explicite. C'est la fondation correcte du refus honnête.

Limite : le champ texte libre `text` (exploité pour les fiches annexes) n'est présent que sur 13 444 fiches (28,5 %), et `debouches` structuré sur 5,2 %. Beaucoup de fiches sont donc "maigres" (peu de contenu exploitable), ce qui dégrade le retrieval sémantique pour les questions de découverte (métier -> débouchés).

---

## 6. Biais d'indexation (à surveiller, AI Act)

- Voie agricole : 546 fiches matchent l'heuristique agricole (BTSA, lycée agricole, agronomie). Donc pas totalement absente (divergence doc/réel n°4 vs "Parcoursupagri non intégré"), mais probablement sans les chiffres d'admission Parcoursup (à vérifier). Couverture partielle.
- Sur-représentation possible des formations bien dotées en données : les fiches Parcoursup (avec taux d'accès, places) sont structurellement plus "citables" que les fiches RNCP/ONISEP nationales sans région ni chiffres. Le système répond donc mieux sur les formations Parcoursup que sur le reste - un biais d'indexation indirect qui favorise un type de formation, à documenter au titre de l'audit de sources exigé par l'AI Act.

---

## 7. Synthèse L3 - findings data priorisés

| # | Finding (mesuré) | Sévérité | Impact observé en L1 |
|---|---|---|---|
| D1 | Région absente sur 45,9 % des fiches eligible (doc disait 41,5 %) | HIGH | edge_geo : contraintes régionales ratées/sur-élargies |
| D2 | 18 012 fiches avec `ville` = chaîne vide (piège "présent mais vide") | HIGH | filtres géo silencieusement faux |
| D3 | Taux d'accès Parcoursup sur 17 % seulement ; débouchés structurés 5 % | HIGH | sur-refus + substitution de métrique |
| D4 | 7,4 % des blocs insertion_pro tout-à-null (present-but-empty) | MEDIUM | refus ou substitution si testé "présent" |
| D5 | Stats d'insertion laggées 2-7 ans ("données fraîches" à nuancer) | MEDIUM | risque de survente dans le pitch |
| D6 | Fiches maigres : `text` 28,5 %, `debouches` 5,2 % | MEDIUM | retrieval sémantique faible sur découverte métier |
| D7 | Biais d'indexation pro-Parcoursup (formations mieux dotées = mieux servies) | MEDIUM (AI Act) | inégalité de qualité de réponse par type de formation |

Points forts confirmés : volume réel (47k), diversité des sources (aucune > 17 %), séparation structuré/texte avec null explicite (fondation correcte du refus honnête), DOM-TOM mieux couvert que documenté.

Conclusion L3 : le suspect data est confirmé empiriquement. Le système refuse beaucoup et substitue parfois non pas parce qu'il est mal codé, mais parce que **la donnée citable manque pour une large part du corpus** (chiffres sur 5-28 % selon le champ, région sur 54 %). La fiabilisation passe autant par l'enrichissement et le nettoyage de la data (combler région, purger les ville vides, étendre les débouchés) que par le prompt ou le retrieval. Chaque divergence doc/réel relevée (×4) confirme par ailleurs qu'il ne faut pas piloter ce projet à la doc.
