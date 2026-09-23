# Lot 0 : reference prod et Mistral Large : 2026-09-23_lot0

Commit `ff4e6f2acc`, batterie `5b268bf34d91`, corpus `2e4276e6155b`, juge `opus`.

## Tableau de tete

Note du juge de 1 a 5. **Chiffres adosses** = part des chiffres cites (%, EUR, places) presents dans une fiche que le systeme a exposee sur ce tour ; entre parentheses, le temoin de hasard (memes reponses contre les fiches d'un autre tour). Un systeme sans fiche est a 0 par construction : ses chiffres ne peuvent pas etre montres.

| systeme | tours | erreurs | moy. 4 | references | comprehension | expression | couverture | refus | err. fact. | chiffres cites | adosses (hasard) | corpus seul | non retrouves |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| local | 67 | 0 | 1.99 | 1.91 | 2.06 | 2.07 | 1.9 | 33 % | 24 % | 438 | 58 % (33 %) | 5 % | 37 % |
| mistral_large_norag | 67 | 0 | 3.2 | 2.42 | 3.22 | 3.51 | 3.64 | 0 % | 94 % | 805 | 0 % (n/a) | 7 % | 93 % |

**Corpus seul** : chiffre absent des fiches exposees mais present dans une des 5 fiches que la ligne designe (BM25). Indicatif : calibre le 23/09, cet ancrage ne retrouve que 37 a 60 % des chiffres adosses et coincide par hasard sur ~15 % des chiffres. **Non retrouve** ne veut pas dire faux.

## Par domaine (moyenne des 4 criteres, n tours juges)

| domaine | local | mistral_large_norag |
|---|---|---|
| arts-design-archi | 2.31 (4) | 3.62 (4) |
| droit-eco-gestion | 1.93 (10) | 3.25 (10) |
| informatique | 2.07 (14) | 3.21 (14) |
| ingenieur | 1.71 (6) | 3.46 (6) |
| lettres-langues-shs | 2.07 (7) | 2.86 (7) |
| maths-sciences | 1.9 (5) | 3.2 (5) |
| sante | 1.88 (6) | 3.17 (6) |
| sport | 2 (1) | 2.5 (1) |
| transversal | 1.96 (13) | 3.12 (13) |
| voie-pro | 2.5 (1) | 3.5 (1) |

Chiffres adosses par domaine :

| domaine | local | mistral_large_norag |
|---|---|---|
| arts-design-archi | 55 % (22) | 0 % (45) |
| droit-eco-gestion | 67 % (54) | 0 % (129) |
| informatique | 59 % (134) | 0 % (230) |
| ingenieur | 100 % (14) | 0 % (68) |
| lettres-langues-shs | 31 % (102) | 0 % (81) |
| maths-sciences | 91 % (23) | 0 % (62) |
| sante | 76 % (17) | 0 % (52) |
| sport | 100 % (2) | 0 % (19) |
| transversal | 58 % (65) | 0 % (112) |
| voie-pro | 100 % (5) | 0 % (7) |

## Distribution du critere references

| systeme | 1 | 2 | 3 | 4 | 5 | part >= 4 |
|---|---|---|---|---|---|---|
| local | 21 | 32 | 13 | 1 | 0 | 1 % |
| mistral_large_norag | 1 | 40 | 23 | 3 | 0 | 4 % |

## Causes d'echec (quand references < 3 ou couverture < 3)

- local : generation 49, retrieval 9 (total 58)
- mistral_large_norag : generation 36, retrieval 3, data_absente 2 (total 41)

## Multi-tour contre premier tour (references / comprehension)

| systeme | tour 0 | tours >= 1 | n tours >= 1 |
|---|---|---|---|
| local | 1.93 / 2.07 | 1.71 / 2 | 7 |
| mistral_large_norag | 2.43 / 3.18 | 2.29 / 3.57 | 7 |

## Pires tours de local

- L06.0 1/1/2/1 [generation] "Prepa MPSI a Louis-le-Grand ou ecole d'ingenieur post-bac type INSA Lyon, qu'est-ce qui es" : La question ne portait pas sur un classement mais sur la sécurité du parcours (MPSI LLG avec risque de concours vs INSA Lyon en 5 ans intégrés) : il fallait com
- L21.0 1/1/2/1 [generation] "BTS SIO option SLAM : c'est quoi le taux d'insertion et le salaire a la sortie ? Et apres " : Le BTS SIO option SLAM est une formation archi-connue : il fallait donner l'essentiel (insertion d'environ 60-70 % des diplomes en emploi, salaire de debut auto
- L25.2 1/1/2/1 [retrieval] 'Entre licence MIASHS et prepa ECG, tu prends quoi a ma place ?' : La reponse esquive totalement une question de conseil tres standard (MIASHS vs prepa ECG) alors qu'une comparaison des deux voies relevait de la culture general
- E08.0 1/1/2/1 [generation] 'Je veux faire une annee de cesure apres ma L2 pour voyager et bosser. Comment on fait et e' : La réponse esquive totalement la question (césure : demande écrite au président/directeur d'établissement, dossier motivé, conservation du droit à réinscription
- E16.0 1/1/2/1 [generation] 'Je veux partir un semestre en Erasmus pendant ma L3 LLCER anglais. Comment ca marche et il' : La réponse est hors sujet : elle recycle des fiches Parcoursup (taux d'accès, places) sans aucun intérêt pour un étudiant déjà en L3, et élude la question des b
- E21.0 1/1/2/1 [generation] 'Avec une L3 AES, quels concours de la fonction publique je peux passer directement ?' : Il fallait repondre sur le fond avec des references de culture generale et verifiables (concours de categorie A : IRA, attache territorial, inspecteur/controleu
- E29.0 1/1/2/1 [generation] "J'ai un BTS et 2 ans de boulot, je veux reprendre en licence pro. Je passe par Parcoursup " : La question est purement procédurale : l'admission en licence professionnelle (3e année) se fait par candidature directe auprès de l'université (e-candidat), ho
- L14.1 1/2/2/1 [retrieval] 'Je suis en terminale ST2S a Marseille avec 12 de moyenne. Quelles sont mes chances en IFSI' : La reponse esquive totalement une question standard : il fallait citer les 4 IFSI/groupements d'Aix-Marseille sur Parcoursup, les criteres d'examen du dossier (
- L24.0 1/1/2/2 [generation] "J'ai trop peur de me tromper de voie et de gacher ma vie. Comment on choisit ?" : Proposer un master de psychologie à Nanterre (avec taux d'admission et salaire) à un lycéen angoissé est totalement hors sujet, et les mentions '[source S1]' so
- E05.0 1/2/2/1 [generation] "Je suis en BUT GEII 2e annee. Je veux integrer une ecole d'ingenieur apres, comment ca mar" : La question portait sur le FONCTIONNEMENT des admissions paralleles apres BUT (admission sur titre en 1re annee du cycle ingenieur, concours/banques comme Polyt

## Erreurs factuelles relevees par le juge

### local (16)

- E01.0 : Le portail Droit de l'Université de Montpellier annoncé avec seulement 30 places est invraisemblable (plusieurs centaines de places) ; de plus proposer une licence de Droit à un étudiant qui veut quit
- E05.0 : Les chiffres cites (taux d'acces 25 %, 145 places a Polytech Sorbonne ; 96 %, 15 places a l'ECE) concernent l'admission POST-BAC via Parcoursup, pas les admissions paralleles apres un BUT : les presen
- E06.0 : Les chiffres cités (96 places / 1717 candidats / dernier appelé rang 161) sont des statistiques de la campagne passée, présentées à tort comme des 'places disponibles' pour la rentrée ; de plus l'inti
- E09.0 : Depuis la reforme entree en vigueur pour la session 2026, les concours d'enseignement du 2nd degre (dont le CAPES d'histoire-geographie) sont passes en fin de licence (bac+3), suivis d'un master MEEF 
- E11.0 : La réponse affirme ne pas avoir de formation 'exactement' intitulée data science alors qu'elle cite juste après le master 'MATHEMATIQUES ET APPLICATIONS — Data science' d'Angers ; les salaires médians
- E11.1 : Affirmer qu'il n'existe pas de master data science a Grenoble est faux : l'UGA propose notamment le master MSIAM (Mathematiques et applications, parcours Data Science) et le master Informatique (parco
- E17.0 : Les chiffres cites (admis/candidats, rang du dernier appele) proviennent de MonMaster, qui concerne l'entree en M1, alors que la reponse les presente comme une voie de reorientation 'en M2' : l'admiss
- E20.0 : L'assistant ecarte les masters au motif qu'ils 'demandent un bac+3, donc moins adaptes pour un chemin court' : l'etudiant est en L2, il n'est qu'a un an de la L3 psycho, et le master Ergonomie/Psychol
- E21.0 : Le niveau licence (bac+3) ouvre les concours externes de categorie A (attache territorial, IRA/attache d'Etat, inspecteur des finances publiques, CRPE...), pas seulement la categorie B ; de plus propo
- L03.0 : Le PASS de l'Université de Bordeaux est annoncé avec '45 places' : chiffre invraisemblable, la capacité réelle du PASS bordelais se compte en plusieurs centaines/milliers de places. Par ailleurs propo
- L11.0 : Un taux d'acces de 62 % est qualifie de 'selective', ce qui est contradictoire/inexact ; et les deux exemples cites sont des formations STAPS alors que la reponse affirme presenter des alternatives a 
- L13.0 : L'assistant affirme qu'aucune licence Informatique n'existe a Toulouse, alors que la Licence Informatique de l'Universite Toulouse III - Paul Sabatier (et la double licence Maths-Informatique MIDL) fi
- L13.1 : Affirmer qu'aucune licence informatique n'existe a Toulouse est faux : l'Universite Toulouse III - Paul Sabatier propose une Licence Informatique (portail MIASHS/Informatique) sur Parcoursup, et l'IUT
- L17.0 : L'admission à Sciences Po Paris n'est pas 'uniquement sur dossier' : la procédure Parcoursup comprend 4 épreuves dont un entretien oral d'admission pour les candidats présélectionnés (et des écrits po
- L18.0 : L'affirmation d'un « concours commun en 1re année » est fausse : l'admission post-bac (ex-voie C/ Parcoursup) se fait sur dossier + entretien lors de la candidature, pas par un concours en première an
- L25.1 : Proposer de « viser directement un master après une prépa » est une procédure erronée : une CPGE mène aux concours d'écoles d'ingénieurs/commerce (ou à une L3 par équivalence), pas directement à un ma

### mistral_large_norag (63)

- E01.0 : Les prepas 'ECE/ECS' n'existent plus depuis la reforme de 2021 : c'est la voie unique ECG (Lycee Joffre propose bien une ECG). Par ailleurs plusieurs chiffres semblent inventes (taux d'acces ~60% en r
- E02.0 : Taux d'acces (~60%, ~55%, ~30%...) et taux d'insertion/salaires presentes comme des donnees 2024-2025 sont inventes ; MonMaster ne publie pas de 'taux d'admission par moyenne'. Paris-Saclay decrit com
- E03.0 : Le MIAGE de Lyon est porté par Lyon 3 (IAE), pas Lyon 2 ; OVH est une entreprise de Roubaix et non une startup nantaise ; les taux d'admission (20%, 40%, 50%) et taux d'insertion detailles semblent in
- E04.0 : Plusieurs faits inventes ou faux : le taux de '60-70% des ex-PCSI obtenant une L2 directe (enquetes des universites 2024)' et les '40 ECTS valides a Paris-Saclay' sont des chiffres fabriques ; l'admis
- E05.0 : Nombreux taux d'admission chiffres precis apparemment inventes (ENI Brest ~30% pour les BUT GEII en 2024, INP 20-25%, UTC 15-20%...) ; le reseau Polytech compte environ 16-17 ecoles et non 15 ; la pre
- E06.0 : Plusieurs elements faux : il n'existe pas de master 1 public 'hors plateforme' non selectif que l'on obtiendrait en ecrivant aux secretariats (tous les M1 publics passent par MonMaster) ; l'ISTHIA (To
- E07.0 : Chiffres largement inventés : l'enquête d'insertion du MESR donne pour le master Sciences humaines et sociales / sociologie un taux d'insertion à 30 mois plutôt autour de 84-88% (pas 90-92%) et un sal
- E08.0 : Erreurs majeures : pendant une cesure l'etudiant RESTE inscrit a l'universite (droits d'inscription souvent reduits, CVEC) et CONSERVE son statut etudiant ; la bourse peut meme etre maintenue sur deci
- E09.0 : La réponse ignore la réforme majeure de 2025 : depuis la session 2026, les concours d'enseignement du second degré (dont le CAPES d'histoire-géographie) se passent en fin de licence (bac+3), suivis d'
- E10.0 : EPITA presentee comme 'ecole publique' (elle est privee, ~9-10k€/an) ; BTS SIO au lycee Louis-le-Grand : inexistant ; 'retenter PASS en L2' est faux (le PASS n'est redoublable ni reintegrable, on pass
- E11.0 : La candidature en master passe par MonMaster.gouv.fr, pas par Parcoursup (erreur repetee deux fois, y compris dans les 'ressources'). Plusieurs taux d'admission/salaires sont inventes et non sourcable
- E11.1 : URLs inventees (master-maths-grenoble.fr, master-info-grenoble.fr, master-data-science-lyon.fr), 'Master Data et Apprentissage' a Polytech Annecy-Chambery (Polytech est une ecole d'ingenieurs, ce mast
- E12.0 : ISAE-SUPAERO et CentraleSupelec ne recrutent pas en admission parallele des titulaires d'une licence d'economie (profils scientifiques uniquement) : conseil hors sujet. Le seuil TAGE MAGE annonce (>40
- E13.0 : Plusieurs faits faux : (1) le nombre de contrats doctoraux ministeriels est d'environ 4 000-5 000/an en France, pas 1 500-2 000 ; (2) le calendrier annonce est inverse : les campagnes de contrats doct
- E14.0 : Manque et contredit la regle centrale : depuis la loi, l'apprenti dispose de 3 mois apres le debut de la formation pour signer son contrat (statut de stagiaire de la formation professionnelle pendant 
- E15.0 : Deux erreurs majeures : (1) le DCG n'est pas 'le seul diplôme qui ouvre au DSCG' — un Master CCA (ou tout master, avec dispenses d'UE) y donne accès, et la voie LP puis L3/Master CCA mène aussi au DEC
- E16.0 : Le Royaume-Uni ne participe plus a Erasmus+ depuis le Brexit (2021) : UCL, Edinburgh, Glasgow, Liverpool, King's ne sont pas des destinations Erasmus+ et il n'existe pas de bourse Erasmus+ 'de 350 EUR
- E17.0 : Incohérence de calendrier : en septembre 2026, les candidatures pour la rentrée 2026-2027 sont closes ; dire « postule dès maintenant, dossiers ouverts jusqu'en mars-avril 2027 » vise en réalité la re
- E18.0 : "MS Management de l'Innovation à Centrale Paris" : l'École Centrale Paris n'existe plus depuis 2015 (fusion en CentraleSupélec). Le chiffre "+10-20% de salaire, source CGE 2023" ne correspond à aucune
- E19.0 : En cas de divorce, le Crous ne retient PAS les revenus des deux parents : il prend en compte ceux du parent qui a la charge de l'etudiant (celui designe par le jugement ou chez qui il est rattache fis
- E20.0 : L'École de design Nantes Atlantique ne délivre pas de DN MADE (diplôme national préparé en lycées/écoles publiques) mais son propre bachelor/cycle master visé. Par ailleurs plusieurs intitulés et surt
- E21.0 : Les concours de catégorie B (rédacteur territorial, contrôleur des finances publiques, secrétaire administratif, gardien de la paix) sont de niveau bac, pas bac+3 : la réponse les présente comme des c
- E22.0 : Plusieurs formations citées ne passent pas par MonMaster (HEC Paris MSc, ESSEC, Sciences Po Paris/Lille, EHESS pour partie) : la plateforme concerne les masters universitaires publics. Les pondération
- E23.0 : Les masters ne se candidatent pas sur Parcoursup (c'est monmaster.gouv.fr), et les licences pro non plus (candidature directe aupres des IUT/universites). Le calendrier propose (decembre 2025 / janvie
- E23.1 : Le Master 'Sécurité des Systèmes Informatiques' est à Sorbonne Université, pas à Paris Cité ; CY Tech est un établissement public dont le master ne coûte pas 6 000€/an ; JPO annoncées 'novembre 2025'/
- E23.2 : Calendrier totalement decale : la reponse dit 'd'ici decembre 2025 postule sur MonMaster' et 'pour la rentree septembre 2026, postule des janvier 2026' alors qu'on est en septembre 2026 (la phase MonM
- E24.0 : Plusieurs erreurs graves : (1) la candidature en IFMK depuis un PASS/L.AS ne se fait PAS via Parcoursup mais via la procédure d'admission santé de l'universite (validation de 60 ECTS + dossier/oral) ;
- E25.0 : Procédure fausse : l'admission en DEP après une licence se fait par le concours commun paysage (admission sur titre / en 1re ou 2e année), pas via Parcoursup. 'ENSAP Marseille' n'existe pas (Marseille
- E26.0 : Le taux national de reussite en L1 en un an est plutot de l'ordre de 40 % (passage L1->L2 ~45 % selon le SIES), pas 30 %. Surtout, les taux par universite cites (22 % Paris Cite, 24 % Lyon 2, 18 % Par
- E27.0 : Plusieurs inexactitudes : 'Université de Rennes 1' n'existe plus depuis 2023 (Université de Rennes) ; l'ESILV est une école d'ingénieurs (donc pas un 'master universitaire privé') ; Epitech n'est pas 
- E28.0 : Le chiffre "15% des étudiants en licence à Paris 1 prennent une césure chaque année" est invraisemblable/inventé (la césure concerne quelques % au plus). Passerelle 1 s'adresse aux bac+2 pour entrer e
- E29.0 : Parcoursup est une procédure post-bac : les licences professionnelles (L3) n'y figurent pas, il n'y a pas d'« exceptions en Île-de-France ». Le « Bachelor universitaire (BUT) en 3 ans » n'est pas une 
- E30.0 : Le diplôme français d'orthophoniste (certificat de capacité) dure 5 ans (grade master) et non 4, et l'admission se fait via Parcoursup depuis 2020 (dossier + épreuves), pas par 'concours après une L1 
- L01.0 : 42 délivre bien des titres RNCP (niveau 6 et 7) : dire 'pas de diplôme reconnu par l'État' est faux. L'IUT Lumière Lyon 2 ne propose pas de BUT Informatique (offre orientée GEA, TC, science des donnée
- L02.0 : Plusieurs approximations/erreurs : la poursuite en licence professionnelle après un BUT n'a plus de sens (la LP a été intégrée au BUT, qui est déjà bac+3 à grade licence) ; l'admission en école d'ingé
- L03.0 : Deux erreurs : la réforme autorise au maximum 2 candidatures aux études de santé en premier cycle (pas 3 tentatives en L2 et L3) ; et les frais d'inscription du PASS sont ceux d'une licence (~175 €), 
- L05.0 : L'apprentissage n'est pas 'sans limite' sur Parcoursup : 10 vœux supplémentaires maximum en apprentissage. L'inscription/création de dossier n'ouvre pas en décembre mais mi-janvier (décembre = ouvertu
- L06.0 : Plusieurs chiffres inventés ou faux : « 100% des MPSI/MP* de LLG intègrent une école du Top 20 » (faux, il y a des redoublements et des échecs), « Polytechnique prend ~50 élèves de LLG sur 400 candida
- L07.0 : Le CFA AFORP est un organisme d'Ile-de-France (Asnieres, Drancy, Mantes, Issy) et n'a pas de site a Lille ; il est de plus decrit a tort comme 'prive sous contrat a 500 euros/an' alors qu'un CFA est g
- L08.0 : Plusieurs erreurs : la catégorie B n'est pas 'niveau bac+3' (elle est accessible au bac, ex. rédacteur territorial, gardien de la paix) ; les 'huissiers de justice' sont devenus commissaires de justic
- L09.0 : Sorbonne Université ne propose pas de licence de psychologie (l'offre francilienne publique : Université Paris Cité, Paris Nanterre, Paris 8, Sorbonne Paris Nord/Bobigny, Paris-Est Créteil, Évry). Le 
- L10.0 : Emile Cohl (Lyon) est une ecole privee payante et ne delivre pas de DNMADE ; les ecoles des beaux-arts (Bordeaux) delivrent le DNA/DNSEP, pas le DNMADE. Le DNMADE en lycee public n'a pas de 'frais d'i
- L11.0 : Le 'BTS Métiers de l'Esthétique-Cosmétique-Parfumerie option Sport' n'existe pas (les options du BTS MECP sont Management, Formation-Marques, Cosmétologie) et n'a rien à voir avec les métiers du sport
- L12.0 : Frais sous-estimes : EPITA, ESILV, ISEP, ECE, EFREI sont plutot a 9 000-11 500 EUR/an (et non 5 000-9 000). Les reductions annoncees (-30% ESILV, -50% ISEP) et le 'taux d'acces 20-30% des boursiers' s
- L13.0 : Chiffres et sources apparemment inventes : 'ORESIPE 2024', '1 200 demandes pour 500 places' en L1 info UT3, '~30% de taux d'admission' en BUT, '~20%' pour une double licence maths-info, insertion 90%/
- L13.1 : Plusieurs erreurs : l'entrée en BUT2 après une L1 ne passe pas par Parcoursup (candidature directe/passerelle auprès de l'IUT) et aucun quota de 10-20% de places réservées aux réorientés n'existe ; l'
- L14.0 : Les frais annonces sont faux : en IFSI public la formation est financee par la Region, l'etudiant ne paie que les droits d'inscription nationaux (~175 EUR) + la CVEC (~105 EUR), pas '500 EUR/an de fra
- L14.1 : Depuis la reforme de 2019, les IFSI recrutent uniquement sur dossier via Parcoursup : il n'y a plus d'entretien/oral de selection (l'affirmation sur les 'IFSI de Nice ou Aix qui ajoutent un oral' est 
- L15.0 : Plusieurs elements faux ou inventes : la 'Prépa recherche ENS Paris-Saclay parcours Humanités' n'existe pas (l'ENS Paris-Saclay propose les CPGE D1/D2 droit-économie) ; le 'Quiz métiers' de Parcoursup
- L16.0 : Le parcours du BUT GEA cite est invente : il n'existe pas de parcours 'Gestion et Pilotage des Ressources Financieres (GPME)' (GPME est un BTS). Les vrais parcours du BUT GEA sont : Controle de gestio
- L17.0 : La procédure d'admission en 1re année de Sciences Po Paris (via Parcoursup depuis 2021) ne comporte PAS d'épreuves écrites en ligne à faire chez soi (analyse de document, réflexion personnelle, langue
- L18.0 : Erreur majeure : depuis 2021 il EXISTE une voie d'accès post-bac aux 4 ENV (Alfort, Oniris Nantes, VetAgro Sup Lyon, ENVT Toulouse) via Parcoursup (concours post-bac, ~160-200 places/an), ainsi qu'une
- L19.0 : "Master LEA Traduction à Lille 3" : l'université Lille 3 n'existe plus depuis 2018 (Université de Lille). Plusieurs chiffres sont presentes comme officiels alors qu'ils semblent inventes ("enquete 202
- L20.0 : Chiffres ENSA Nantes invraisemblables (dans les faits ~4000-5000 candidats pour environ 190 places, taux d'acces autour de 5-8%, pas 15-20% ni 1200 candidats) ; l'entretien systematique a Nantes compt
- L23.0 : ISAE-SUPAERO n'est PAS une ecole post-bac et ne recrute pas via le concours GEIPI-Polytech : c'est une ecole post-CPGE (concours commun Mines-Ponts/X, voie universitaire). ESTACA n'a pas de campus a T
- L24.0 : Plusieurs chiffres semblent inventés ou non sourçables : « 50% des étudiants se réorientent dans les 2 ans (MESRI 2024) », « 85% d'insertion à 6 mois » pour le BUT Carrières Juridiques, « 90% d'embauc
- L25.0 : Plusieurs affirmations fausses ou invraisemblables : les licences de maths ne sont pas 'sélectives en L2/L3' avec seulement 30% de passage ; Polytechnique ne recrute pas 'sur titre' après licence ; le
- L25.1 : La prépa 'ECE' n'existe plus depuis 2021 (voie unique ECG). Le BUT STID n'est pas proposé à l'IUT de Rennes mais à l'IUT de Vannes (Université Bretagne Sud). Les taux d'accès et salaires cités sont do
- L25.2 : Plusieurs faits faux : il n'y a pas de stage obligatoire en 1re annee de prepa ECG ; Saint-Martin (Rennes) est un etablissement prive sous contrat, donc pas 'gratuit' ; Black-Scholes/series temporelle
- L26.0 : La prepa Cine-Sup n'est pas a Lyon mais au lycee Guist'hau a Nantes (c'est la CPGE publique de reference pour la Femis/Louis-Lumiere). Par ailleurs plusieurs chiffres semblent inventes (taux d'inserti
- L27.0 : Le certificat pour les aménagements d'examens à l'université est établi gratuitement par le médecin du service de santé étudiante (SSE/SUMPPS) ou un médecin désigné par la CDAPH, pas par un 'médecin a
- L28.0 : La durée de stage en BUT est de 22 à 26 semaines sur les 3 ans (référentiel BUT), pas 10 à 12 semaines. Plusieurs chiffres semblent inventés (taux de réussite L3 ~75 %, 3 à 5 candidats par place en IU
- L30.0 : Calendrier faux (on est en septembre 2026 : les voeux Parcoursup seraient janvier-mars 2027, pas decembre 2025 ; le DSE se depose de mars a fin mai, pas en janvier). Confusion 'licences selectives' :
