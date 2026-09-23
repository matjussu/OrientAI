# Gate C : 20/20 requêtes justes

Requêtes : `../_orientai-ref/verticale-2026-09/gate_c/requetes_gate_c.json` (sha256 `227a2c9bfaf6`), base `/home/matteo_linux/projets/OrientIA-etape-c/data/processed/base_etape_c.sqlite`.
Rejouer : `python -m src.eval.gate_c --requetes <fichier>`.

| Req. | Mode | Juste | Attendues | Rendues | Manquantes | En trop | Ordre | Valeurs |
|---|---|---|---|---|---|---|---|---|
| C01 | exact | oui | 5 | 5 | - | - | - | 0/0 |
| C02 | exact | oui | 2 | 2 | - | - | - | 0/0 |
| C03 | exact | oui | 3 | 3 | - | - | - | 6/6 |
| C04 | exact | oui | 11 | 11 | - | - | - | 0/0 |
| C05 | exact | oui | 2 | 2 | - | - | - | 6/6 |
| C06 | exact | oui | 7 | 7 | - | - | - | 0/0 |
| C07 | exact | oui | 4 | 4 | - | - | - | 12/12 |
| C08 | exact | oui | 16 | 16 | - | - | - | 32/32 |
| C09 | exact + ordre | oui | 4 | 4 | - | - | oui | 0/0 |
| C10 | exact + ordre | oui | 3 | 3 | - | - | oui | 0/0 |
| C11 | exact | oui | 3 | 3 | - | - | - | 0/0 |
| C12 | exact | oui | 3 | 4 | - | - | - | 0/0 |
| C13 | exact | oui | 4 | 4 | - | - | - | 0/0 |
| C14 | vide | oui | 0 | 0 | - | - | - | 0/0 |
| C15 | exact | oui | 13 | 13 | - | - | - | 13/13 |
| C16 | exact | oui | 3 | 3 | - | - | - | 0/0 |
| C17 | exact | oui | 3 | 3 | - | - | - | 0/0 |
| C18 | exact | oui | 6 | 6 | - | - | - | 0/0 |
| C19 | exact | oui | 6 | 6 | - | - | - | 0/0 |
| C20 | exact | oui | 7 | 7 | - | - | - | 0/0 |

## Détail des requêtes

### C01 : Quelles formations en informatique (BUT Informatique, licence Informatique, BTS SIO) a moins de 80 km de Rodez ?

Filtres : type bts ou but ou las ou licence ; filière Informatique ou Services informatiques aux organisations ; hors apprentissage ; à moins de 80 km de Rodez (12202), à vol d'oiseau [chercher_formations, session 2025]

### C02 : Quels BUT Informatique des Hauts-de-France ont au moins 35 % de bacheliers technologiques parmi leurs admis neo-bacheliers ?

Filtres : type but ; filière Informatique ; région Hauts-de-France ; part_bac_techno >= 35 [chercher_formations, session 2025]

### C03 : Je suis en bac pro CIEL : quels BTS SIO ou BTS CIEL option A (informatique et reseaux) a moins de 30 km de Rennes, avec leurs places et la part de bac pro parmi les admis neo-bacheliers ?

Filtres : type bts ; filière Services informatiques aux organisations ou Cybersécurité, Informatique et réseaux, ELectronique - Option A : Informatique et réseaux ; hors apprentissage ; à moins de 30 km de Rennes (35238), à vol d'oiseau [chercher_formations, session 2025]

### C04 : Je veux faire de l'info en alternance pour etre paye : quels BUT Informatique ou BTS SIO en apprentissage dans le Nord (59) ?

Filtres : type bts ou but ; filière Informatique ou Services informatiques aux organisations ; en apprentissage ; département 59 [chercher_formations, session 2025]

### C05 : Les BUT Informatique de Seine-Saint-Denis : comment a evolue leur taux d'acces de 2023 a 2025 ?

Filtres : type but ; filière Informatique ; département 93 [chercher_formations, session 2025]

### C06 : Quelles formations en informatique existent en Martinique apres le bac ?

Filtres : type bts ou but ou las ou licence ; filière Informatique ou Services informatiques aux organisations ou Cybersécurité, Informatique et réseaux, ELectronique - Option A : Informatique et réseaux ou Cybersécurité, Informatique et réseaux, ELectronique - Option B : Electronique et réseaux ; hors apprentissage ; département 972 [chercher_formations, session 2025]

### C07 : Je suis en L3 MIASHS a Toulouse : quels masters MIAGE en Occitanie, lesquels sont en alternance, avec leur capacite et leur nombre de candidats ?

Filtres : mention contenant « MIAGE » ; région académique Occitanie [chercher_masters, session 2025]

### C08 : PASS ou LAS a Rennes : quelles formations existent, avec leurs places et leur taux d'acces ?

Filtres : type las ou pass ; commune 35238 [chercher_formations, session 2025]

### C09 : Je suis en ST2S : quels IFSI a moins de 60 km de Limoges, du plus accessible au moins accessible ?

Filtres : type ifsi ; à moins de 60 km de Limoges (87085), à vol d'oiseau ; trié par taux_acces décroissant [chercher_formations, session 2025]

### C10 : Bac pro ASSP : quels sont les 3 IFSI du Nord qui admettent la plus grande part de bacheliers professionnels parmi leurs admis neo-bacheliers ?

Filtres : type ifsi ; département 59 ; trié par part_bac_pro décroissant [chercher_formations, session 2025]

### C11 : Ou se former au diplome d'Etat d'ergotherapeute en Normandie ?

Filtres : filière D.E Ergothérapeute ; région Normandie [chercher_formations, session 2025]

### C12 : Manipulateur radio : quels DE et DTS imagerie a moins de 50 km de Lyon, avec leur taux d'acces ?

Filtres : filière D.E manipulateur/trice en électroradiologie médicale ou DTS Imagerie médicale et radiologie thérapeutique ; à moins de 50 km de Lyon (69123), à vol d'oiseau [chercher_formations, session 2025]

### C13 : Quelles formations d'orthophoniste ont un taux d'acces inferieur a 8 % ?

Filtres : filière Certificat de capacité d'Orthophoniste ; taux_acces < 8 [chercher_formations, session 2025]

### C14 : Y a-t-il un PASS a Poitiers ?

Filtres : type pass ; commune 86194 [chercher_formations, session 2025]

### C15 : Le PASS de Lille : quelle part des etudiants passe en medecine, maieutique, odontologie, pharmacie ou kine ?

Filtres : type pass ; commune 59350 [chercher_formations, session 2025]

### C16 : Quelles licences de mathematiques a moins de 30 km de Rennes ?

Filtres : type las ou licence ; filière Mathématiques ; à moins de 30 km de Rennes (35238), à vol d'oiseau [chercher_formations, session 2025]

### C17 : Ou faire une licence MIASHS dans les Hauts-de-France ?

Filtres : type las ou licence ; filière Mathématiques et informatique appliquées aux sciences humaines et sociales ; région Hauts-de-France [chercher_formations, session 2025]

### C18 : 12 de moyenne : quelles prepas MPSI, MP2I ou PCSI a moins de 50 km de Valenciennes ont un taux d'acces d'au moins 50 % ?

Filtres : type cpge ; filière MPSI ou MP2I ou PCSI ; à moins de 50 km de Valenciennes (59606), à vol d'oiseau ; taux_acces >= 50 [chercher_formations, session 2025]

### C19 : Je suis en STI2D : quelles prepas TSI en Occitanie ?

Filtres : type cpge ; filière TSI ; région Occitanie [chercher_formations, session 2025]

### C20 : A La Reunion, quelles prepas scientifiques (MPSI, MP2I, PCSI) et licences de maths ?

Filtres : type cpge ; filière MPSI ou MP2I ou PCSI ; département 974 [chercher_formations, session 2025] PUIS type las ou licence ; filière Mathématiques ; département 974 [chercher_formations, session 2025]

