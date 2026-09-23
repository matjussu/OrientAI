# Relecture à la main de 30 coûts Onisep (étape B-1)

Relu le 23/09/2026 par Claudette, sur le corpus `formations_etape_b1.json` (sha256 `44a385c53c95`). Tirage : 30 fiches à graine fixe (30) parmi les 533 fiches des trois domaines dont le coût vient d'Onisep (`onisep_uai_intitule` ou `onisep_uai_famille`). Pour chacune, la ligne Onisep citée par la fiche (identifiant `AF.`) est relue dans le CSV verrouillé : même lieu (UAI), même formation, même texte de coût.

L'égalité du texte de coût avec la source est aussi contrôlée par l'audit automatique (`audit_b1_cout_onisep.json`, 45 fiches, 0 écart, contre le dump JSON Onisep retéléchargé). Cette relecture porte sur ce qu'un contrôle automatique ne juge pas : la ligne Onisep décrit-elle bien la MÊME formation ?

**Verdict : 30 / 30 conformes.** Aucune ligne rattachée à une autre formation ou à un autre lieu.

| # | Fiche | Formation (Parcoursup) | Établissement | Ligne Onisep | Coût publié | Verdict |
|---|---|---|---|---|---|---|
| 1 | 23153 | D.E Infirmier | IFSI CH Ussel (UAI 0190764C) | diplôme d'État d'infirmier | 0 euros en 2026 | conforme |
| 2 | 6939 | BTS - Services - Biologie médicale | Lycée Notre-Dame D'Annay (UAI 0593006X) | BTS biologie médicale | 2660 euros en 2026 (1330 euros par an, formation gratuite et rémunérée en apprentissage) | conforme |
| 3 | 25269 | D.E Infirmier | IFSI CH Avranches-Granville (UAI 0501700B) | diplôme d'État d'infirmier | 0 euros en 2026 | conforme |
| 4 | 23203 | D.E Infirmier | IFSI CH LA ROCHE-SUR-YON (UAI 0851609M) | diplôme d'État d'infirmier | 0 euros en 2026 | conforme |
| 5 | 10929 | BTS - Services - Opticien-Lunetier | Institut et Campus d'Optique (ICO) (UAI 0911264E) | BTS opticien-lunetier | 8340 euros en 2024 (4170 euros par an, gratuit en apprentissage) | conforme |
| 6 | 23228 | D.E Infirmier | IFSI Mary Thieullent CH Le Havre (UAI 0762641H) | diplôme d'État d'infirmier | 0 euros en 2026 | conforme |
| 7 | 23046 | D.E Infirmier | IFSI EPSM DE LA SARTHE (UAI 0721409R) | diplôme d'État d'infirmier | 0 euros en 2026 | conforme |
| 8 | 9467 | CPGE - MPSI | Lycée Stanislas (UAI 0753840S) | classe préparatoire mathématiques, physique et sciences de l'ingénieur (MPSI), 1re année option | 2979 euros en 2025 | conforme (ligne MPSI 1re année ; la voie est la même) |
| 9 | 10231 | BTS - Services - Services informatiques aux organisations | Lycée Saint Remi (UAI 0801479Y) | BTS services informatiques aux organisations option A solutions d'infrastructure, systèmes et r | 1090 euros en 2025 (545 euros par an) | conforme (Parcoursup ne précise pas l'option ; ligne de l'option A citée, texte de coût identique pour les deux options (condition de la règle)) |
| 10 | 26061 | D.E Pédicure-Podologue | INSTITUT NATIONAL DE PODOLOGIE (UAI 0753044B) | diplôme d'État de pédicure-podologue | 28500 euros en 2025 (9500 euros par an) | conforme |
| 11 | 6386 | BTS - Production - Cybersécurité, Informatique et réseaux, ELectronique - Option A : Informatiq | Lycée Charles De Foucauld (UAI 0542408Z) | BTS cybersécurité, informatique et réseaux, électronique option A informatique et réseaux | 3340 euros en 2026 (1670 euros par an) | conforme |
| 12 | 23114 | D.E Infirmier | IFSI CH Dole (UAI 0390987L) | diplôme d'État d'infirmier | 8800 euros en 2026 (possibilité de prise en charge) | conforme (coût écrit avec sa réserve Onisep « possibilité de prise en charge », reprise mot pour mot dans le texte) |
| 13 | 18885 | BTS - Production - Cybersécurité, Informatique et réseaux, ELectronique - Option B : Electroniq | Lycée Saint-Louis (UAI 0260072M) | BTS cybersécurité, informatique et réseaux, électronique option B électronique et réseaux | 2560 euros en 2025 (1280 euros par an, gratuit en apprentissage) | conforme |
| 14 | 11128 | BTS - Services - Services informatiques aux organisations | Lycée Montalembert (UAI 0921484N) | BTS services informatiques aux organisations option A solutions d'infrastructure, systèmes et r | 4914 euros en 2024 (2457 euros par an) | conforme (idem : option non précisée côté Parcoursup, ligne de l'option A citée, coût identique) |
| 15 | 35528 | D.E Ergothérapeute | ILFOMER Institut limousin de formation aux mé (UAI 0875076V) | diplôme d'État d'ergothérapeute | 4170 euros en 2025 (1390 euros par an) | conforme |
| 16 | 23197 | D.E Infirmier | IFSI Neufchateau (UAI 0881510N) | diplôme d'État d'infirmier | 0 euros en 2026 | conforme |
| 17 | 23124 | D.E Infirmier | IFSI de Savoie (UAI 0731230R) | diplôme d'État d'infirmier | 0 euros en 2026 | conforme |
| 18 | 10679 | BTS - Services - Services informatiques aux organisations | Lycée Beaupeyrat (UAI 0870081R) | BTS services informatiques aux organisations option B solutions logicielles et applications mét | 3300 euros en 2025 (1650 euros par an, gratuit en apprentissage) | conforme |
| 19 | 4979 | BTS - Production - Cybersécurité, Informatique et réseaux, ELectronique - Option B : Electroniq | Lycée Pierre Termier (UAI 0381666E) | BTS cybersécurité, informatique et réseaux, électronique option B électronique et réseaux | 1800 euros en 2025 (900 euros par an, gratuit en apprentissage) | conforme |
| 20 | 25271 | D.E Infirmier | IFSI CH Falaise (UAI 0141856S) | diplôme d'État d'infirmier | 0 euros en 2026 | conforme |
| 21 | 48760 | D.E Infirmier | IFSI CH Redon (UAI 0353141Z) | diplôme d'État d'infirmier | 0 euros en 2026 | conforme |
| 22 | 23181 | D.E Infirmier | IFSI- Hospit. Privée (UAI 0341549Z) | diplôme d'État d'infirmier | 0 euros en 2026 | conforme |
| 23 | 26462 | Certificat de capacité d'Orthophoniste | UNITE DE FORMATION ET DE RECHERCHE SANTE (UAI 0860986E) | certificat de capacité d'orthophoniste | 2815 euros en 2026 (563 euros par an) | conforme |
| 24 | 23098 | D.E Infirmier | IFSI CH Public du Cotentin (UAI 0501513Y) | diplôme d'État d'infirmier | 0 euros en 2026 | conforme |
| 25 | 39660 | Certificat de capacité d'Orthoptiste | Université de Caen Normandie - Campus 5 - UFR (UAI 0142409T) | certificat de capacité d'orthoptiste | 1035 euros en 2026 (345 euros par an) | conforme |
| 26 | 24762 | FCIL - secrétariat médical | Centre Scolaire Notre Dame (UAI 0690553B) | FCIL secrétariat médical | 890 euros en 2026 | conforme |
| 27 | 38428 | D.E Infirmier | IFSI CHU Limoges - Antenne de Saint Yrieix la (UAI 0875109F) | diplôme d'État d'infirmier | 0 euros en 2026 | conforme |
| 28 | 6900 | CPGE - MPSI | Lycée Saint Rémi (UAI 0592921E) | classe préparatoire mathématiques, physique et sciences de l'ingénieur (MPSI), 1re année option | 1530 euros en 2025 | conforme (ligne MPSI 1re année ; la voie est la même) |
| 29 | 34546 | D.E Infirmier | IFSI CHU Nîmes - Site : ville d'Uzès (UAI 0301904G) | diplôme d'État d'infirmier | 0 euros en 2027 | conforme (tarif daté 2027 par l'Onisep, repris tel quel) |
| 30 | 23384 | D.E Infirmier | IFSI CH Guillaume Régnier (UAI 0352087D) | diplôme d'État d'infirmier | 0 euros en 2026 | conforme |

Défauts trouvés AVANT cette version, par une relecture identique sur une version antérieure du rattachement, et corrigés dans le code :
- une CPGE PCSI rattachée par la « famille » à une ligne PSI 2e année, alors qu'une ligne PCSI existait (le mot « CPGE » diluait la correspondance) ;
- un BTS CIEL option B rattaché à la ligne de l'option A (la lettre d'option était perdue) ; deux options différentes ne se rattachent plus jamais ;
- la règle « même famille » donnait à un IFSI le coût du diplôme de puéricultrice et à un bachelor celui du diplôme d'ingénieur de l'école : elle est désormais réservée aux CPGE et BTS, sur au moins deux lignes unanimes (tarif du lycée).
