# Verdict probes v2 — typage sur formations NOMMÉES (ordre 2026-06-14-1252)

Auteur : Claudette · Date : 2026-06-14 · Read-only, génération seule (2 index déjà en place).

18 questions sur formations nommées par type (BUT/BTS/Licence/LP/Master/CPGE/ingé/titre
pro/DE), ancien vs nouveau index, temp=0.

---

## VERDICT : gain TYPAGE visible quand la fiche nommée est récupérée — en GROUNDING.

Le gain ne se voit pas au compteur de mots (le modèle CONNAÎT déjà BUT=bac+3 par son
entraînement, donc il citait un niveau même AVANT). Il se voit dans le **sourçage** :
le type/niveau passe d'INFÉRÉ (non sourcé, hallucination potentielle) à SOURCE-GROUNDED.
C'est exactement la thèse anti-hallucination d'OrientAI.

- **La fiche récupérée porte désormais le type** : sur but-01/bts-02/master-01/lic-01,
  la top source passe de type_diplome=None (AVANT) à BUT/BTS/Master/Licence (APRÈS).
- **Type/niveau SOURCÉ ([source SX] attaché)** : AVANT **9/18** -> APRÈS **12/18** (+33%).
- **Aucune régression** : refus 2/18 AVANT = 2/18 APRÈS (bts-01 "SIO" non trouvé, titre-pro
  "accompagnant gérontologie" -> le modèle récupère "Auxiliaire de gérontologie", autre
  cert — comportement honnête identique).

## Exemple net (but-01)

**"Le BUT informatique, c'est quel type de diplôme et à quel niveau ?"**
- AVANT : "Le BUT Informatique est un diplôme national de niveau bac+3..."
  (type/niveau INFÉRÉ par le modèle — la fiche portait type_diplome=None).
- APRÈS : "Type de diplôme : **BUT** (Bachelor Universitaire de Technologie) **[source S2]**.
  Niveau : **bac+3** **[source S2]**."
  (type ET niveau désormais ATTRIBUÉS à la source — claim grounded, vérifiable).

Idem bts-02 ("Type de diplôme : **BTS** [source S1]"), master-01 ("type **Master**
[source S1]"), lic-02 (bloc "Type de diplôme : **Licence** [source S1]" ajouté).

## Lecture

- **Le fill type_diplome marche** : sur une formation nommée, la fiche récupérée porte le
  type, et le générateur le cite EN SOURÇANT. Le bénéfice n'est pas une info nouvelle
  (le modèle connaît les types courants) mais le passage inféré -> grounded : un fait
  auparavant non vérifiable devient attribué au corpus. Pour le validateur anti-hallu et
  le contrat "pas d'invention", c'est le bon mouvement.
- **Pourquoi le bench #1403 ne le montrait pas** : ses probes étaient des COMPARAISONS
  abstraites (BUT vs prépa) qui ne récupéraient pas de fiche. Ici, fiche nommée -> fiche
  récupérée -> type sourcé. La distinction était la bonne intuition de Matteo.
- **Limite honnête** : pour les types très connus (BUT/BTS/Master), la réponse AVANT
  paraissait déjà correcte (modèle compétent) ; le delta est le sourçage, pas le contenu.
  Le gain serait plus fort sur des formations obscures où le modèle ne connaît pas le type.

## Verdict deploy

Confirme le #1403 : le set est **deploy-safe ET porteur d'un gain réel** (typage
source-grounded sur formations nommées, passerelles/RNCP labelling cf #1403), à coût de
régression zéro. GO deploy défendable, sans survendre un bond e2e général.

Artefacts : bench_v2_AVANT.json / bench_v2_APRES.json (18Q), bench_v2_typage_questions_1252.json.
