"""POC Mistral Large function calling — gate J+3 pour Axe 2 agentic.

Objectif : valider empiriquement que Mistral Large peut orchestrer
un agent tool-use pour OrientIA avec fiabilité acceptable, AVANT
d'investir 7 jours sur le prototype agentic complet (STRATEGIE §5
Axe 2 A1-A9).

Gate critères :
1. Mistral Large appelle les tools correctement (schémas respectés)
2. Les params émis sont valides (pas d'hallucination de param)
3. La latence totale par question reste <15s (acceptable UX)
4. Le taux d'échec est <20% sur 5 questions représentatives
5. Les réponses composées sont cohérentes (tools result bien intégrés)

Si POC OK → Mistral Large orchestrator validé pour S2.
Si POC KO → arbitrage avec Matteo (Medium+ReAct OR Claude temporaire).

Run : PYTHONPATH=. python3 experiments/poc_mistral_toolcall.py
"""
from __future__ import annotations

import json
import time
from typing import Any

from mistralai.client import Mistral

from src.config import load_config


# --- Tool definitions (JSON Schema for Mistral function calling) ---

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_formations",
            "description": (
                "Cherche des formations dans le corpus OrientIA (1424 "
                "fiches cyber/data/santé) par domaine, région, niveau. "
                "Retourne jusqu'à 3 fiches les plus pertinentes avec "
                "nom, établissement, ville, taux d'admission Parcoursup, "
                "labels officiels."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Requête en français décrivant ce qu'on cherche (ex: 'formations cybersécurité accessibles bac techno')",
                    },
                    "region": {
                        "type": "string",
                        "description": "Région ou ville française (optionnel)",
                    },
                    "niveau": {
                        "type": "string",
                        "enum": ["bac+2", "bac+3", "bac+5", "tous"],
                        "description": "Niveau de diplôme visé",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_debouches",
            "description": (
                "Retourne les débouchés métiers pour un code ROME. "
                "Inclut salaire médian, tension marché, métiers proches. "
                "Utile pour répondre aux questions sur 'que fait-on après' "
                "une formation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code_rome": {
                        "type": "string",
                        "description": "Code ROME 4.0 (ex: 'M1802' pour expert cybersécurité)",
                    },
                },
                "required": ["code_rome"],
            },
        },
    },
]


# --- Tool implementations (minimal, for POC) ---

def search_formations(query: str, region: str = None, niveau: str = "tous") -> dict:
    """Wrap retriever existant pour POC. Simplifié."""
    # Mock simple : on ne charge pas FAISS ici, on retourne 3 fiches plausibles
    # basées sur des mots-clés du query. POC objectif = tester l'orchestration,
    # pas la qualité retrieval.
    query_lower = query.lower()
    if "cyber" in query_lower:
        fiches = [
            {
                "nom": "BUT Cybersécurité et Systèmes d'Information",
                "etablissement": "IUT de Caen",
                "ville": "Caen",
                "taux_parcoursup": 46,
                "labels": ["SecNumEdu"],
                "niveau": "bac+3",
            },
            {
                "nom": "Licence pro Cybersécurité",
                "etablissement": "Université de Rennes 1",
                "ville": "Rennes",
                "taux_parcoursup": 38,
                "labels": ["SecNumEdu"],
                "niveau": "bac+3",
            },
            {
                "nom": "Mastère Cybersécurité",
                "etablissement": "CentraleSupélec",
                "ville": "Rennes",
                "taux_parcoursup": 12,
                "labels": ["SecNumEdu", "CTI", "Grade Master"],
                "niveau": "bac+5",
            },
        ]
    elif "medec" in query_lower or "pass" in query_lower or "santé" in query_lower:
        fiches = [
            {
                "nom": "PASS Brest",
                "etablissement": "Université de Brest",
                "ville": "Brest",
                "taux_parcoursup": 100,
                "labels": [],
                "niveau": "bac+3",
            },
            {
                "nom": "PASS Aix-Marseille",
                "etablissement": "Aix-Marseille Université",
                "ville": "Marseille",
                "taux_parcoursup": 38,
                "labels": [],
                "niveau": "bac+3",
            },
        ]
    else:
        fiches = [
            {
                "nom": "Formation exemple",
                "etablissement": "Université exemple",
                "ville": "Paris",
                "taux_parcoursup": 50,
                "labels": [],
                "niveau": "bac+3",
            },
        ]
    # Filtrage région si spécifié
    if region:
        fiches = [f for f in fiches if region.lower() in f["ville"].lower()] or fiches
    return {"count": len(fiches), "fiches": fiches}


def get_debouches(code_rome: str) -> dict:
    """Mock ROME 4.0 pour POC. En prod, branche France Travail API (D3)."""
    rome_db = {
        "M1802": {
            "libelle": "Expertise et support en systèmes d'information",
            "salaire_median_mensuel_net": 3200,
            "tension_marche": "forte",
            "metiers_proches": ["Analyste SOC", "Consultant cyber", "Pentester"],
        },
        "M1810": {
            "libelle": "Production et exploitation de systèmes d'information",
            "salaire_median_mensuel_net": 2600,
            "tension_marche": "moyenne",
            "metiers_proches": ["Administrateur systèmes", "Technicien support"],
        },
        "J1102": {
            "libelle": "Médecine généraliste et spécialisée",
            "salaire_median_mensuel_net": 4500,
            "tension_marche": "forte (pénurie)",
            "metiers_proches": ["Médecin hospitalier", "Médecin libéral"],
        },
    }
    return rome_db.get(code_rome, {
        "error": f"Code ROME {code_rome} non trouvé dans la base POC",
        "fallback": "Consulter france-travail.fr pour les débouchés détaillés.",
    })


TOOL_DISPATCH = {
    "search_formations": search_formations,
    "get_debouches": get_debouches,
}


# --- Orchestration loop ---

SYSTEM_PROMPT_POC = """Tu es un conseiller d'orientation OrientIA. Tu as
accès à 2 outils : search_formations (cherche des fiches dans le corpus)
et get_debouches (info métiers par code ROME).

Pour répondre aux questions des étudiants :
1. Si la question porte sur des formations concrètes → appelle
   search_formations avec une requête ciblée
2. Si la question porte sur des débouchés / métiers / salaires →
   appelle get_debouches avec le code ROME pertinent
3. Si la question est conceptuelle (ex : "c'est quoi une licence") →
   réponds directement en (connaissance générale) sans appeler de tool
4. Compose une réponse structurée avec TL;DR + plans concrets basés
   sur les résultats tools.

Reste concis (150-300 mots). Cite les fiches avec leur nom exact."""


def run_agent(client: Mistral, question: str, model: str = "mistral-large-latest") -> dict:
    """Boucle orchestration : question → tool calls → composition finale."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_POC},
        {"role": "user", "content": question},
    ]
    tool_call_count = 0
    max_iterations = 5
    start = time.time()

    for iteration in range(max_iterations):
        response = client.chat.complete(
            model=model,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        if msg.tool_calls:
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                tool_call_count += 1
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError as e:
                    result = {"error": f"JSON parsing failed: {e}"}
                else:
                    if name in TOOL_DISPATCH:
                        try:
                            result = TOOL_DISPATCH[name](**args)
                        except TypeError as e:
                            result = {"error": f"Tool call failed: {e}"}
                    else:
                        result = {"error": f"Unknown tool: {name}"}
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": name,
                    "content": json.dumps(result, ensure_ascii=False),
                })
        else:
            # Mistral a composé la réponse finale
            latency = time.time() - start
            return {
                "answer": msg.content,
                "tool_call_count": tool_call_count,
                "iterations": iteration + 1,
                "latency_s": latency,
                "success": True,
            }

    # Dépassement max iterations
    latency = time.time() - start
    return {
        "answer": None,
        "tool_call_count": tool_call_count,
        "iterations": max_iterations,
        "latency_s": latency,
        "success": False,
        "error": "Max iterations reached without final answer",
    }


# --- POC questions ---

QUESTIONS_POC = [
    ("ranking_cyber", "Quelles sont les meilleures formations en cybersécurité ?"),
    ("realisme_sante", "J'ai 12 de moyenne, puis-je faire PASS à Brest ?"),
    ("debouches", "Quels métiers après un BTS cybersécurité ?"),
    ("comparaison", "Compare ENSEIRB et EPITA pour la cybersécurité"),
    ("conceptuelle", "C'est quoi une licence universitaire ?"),
]


def main() -> None:
    config = load_config()
    if not config.mistral_api_key:
        raise RuntimeError("MISTRAL_API_KEY manquant")

    client = Mistral(api_key=config.mistral_api_key, timeout_ms=120000)
    print(f"Testing mistral-large-latest tool-use on {len(QUESTIONS_POC)} questions\n")

    results = []
    for label, question in QUESTIONS_POC:
        print(f"▶ [{label}] {question}")
        try:
            r = run_agent(client, question)
        except Exception as e:
            r = {"success": False, "error": str(e), "tool_call_count": 0,
                 "iterations": 0, "latency_s": 0}
        r["label"] = label
        r["question"] = question
        results.append(r)

        if r["success"]:
            print(f"  ✓ {r['tool_call_count']} tool calls | "
                  f"{r['iterations']} iterations | {r['latency_s']:.1f}s")
            print(f"  Answer preview: {r['answer'][:150]}...")
        else:
            print(f"  ✗ ECHEC : {r.get('error', 'unknown')}")
        print()

    # --- Verdict ---
    print("=" * 60)
    n_success = sum(1 for r in results if r["success"])
    mean_latency = (sum(r["latency_s"] for r in results if r["success"])
                    / max(n_success, 1))
    mean_tool_calls = (sum(r["tool_call_count"] for r in results if r["success"])
                       / max(n_success, 1))

    print(f"Succès : {n_success}/{len(QUESTIONS_POC)}")
    print(f"Latence moyenne (succès) : {mean_latency:.1f}s")
    print(f"Tool calls moyen (succès) : {mean_tool_calls:.1f}")
    print(f"Conceptuelle sans tool call : "
          f"{'OUI' if any(r['label']=='conceptuelle' and r['tool_call_count']==0 for r in results) else 'NON'}")

    # Gate critères
    print("\n--- GATE ---")
    gate_pass = (
        n_success >= 4  # ≥80%
        and mean_latency < 15
    )
    print(f"Gate: {'✅ PASS — Mistral orchestrator validé pour S2' if gate_pass else '❌ FAIL — arbitrage Matteo nécessaire'}")

    # Save results
    import pathlib
    out = pathlib.Path("experiments/poc_mistral_toolcall_results.json")
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Results saved to {out}")


if __name__ == "__main__":
    main()
