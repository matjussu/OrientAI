#!/usr/bin/env python3
"""generate_golden_qa_v1.py — Sprint 9-data Ordre 2/2 (2026-04-28).

Génère un dataset de Q&A "réponses parfaites de conseiller" via pipeline
agentique 4 phases (research WebSearch → draft → self-critique → refine)
en orchestrant des sub-agents Claude Opus 4.7 via subprocess `claude --print`.

Coût marginal 0$ (utilise quota Claude Max plan de Matteo, pas l'API
Anthropic facturée — décision D5 ADR `2026-04-28-orientia-pivot-pipeline-agentique-claude`).

## Architecture

```
[YAML config 51 prompts × 5-6 seeds]
        ↓
ThreadPoolExecutor (--parallel N)
        ↓
Pour chaque (prompt_id, iteration_idx) :
    Phase 1 : research WebSearch (sub-agent, allowedTools=WebSearch)
        ↓
    Phase 2 : draft Q&A persona conseiller (sub-agent)
        ↓
    Phase 3 : self-critique 4 axes (sub-agent)
        ↓
    Phase 4 : refinement (sub-agent)
        ↓
    Decision policy : keep≥85 / flag 70-85 / drop<70
        ↓
ThreadSafeJsonlAppender → data/golden_qa/golden_qa_v1.jsonl
```

## Rate limiting défensif

- `--parallel N` : 3 par défaut (Max 20x : 5, Max 5x : 2, Pro : 1)
- `--rate-limit-delay D` : délai entre calls (défaut 0.5s)
- `--max-retries R` : retries sur 429 (défaut 3)
- Stop condition : >10 consecutive 429 → abort (Sprint 9-data fallback 500 cas)
- Backoff exponentiel sur 429 : 2^attempt + delay

## Checkpointing

JSONL append-only — si CTRL+C / crash, le prochain run skip les
(prompt_id, iteration) déjà présents dans le fichier output.

## Usage

```bash
# Dry-run 1 prompt × 5 itérations
python scripts/generate_golden_qa_v1.py \\
    --config config/diverse_prompts_50.yaml \\
    --output data/golden_qa/dryrun_test.jsonl \\
    --parallel 2 --filter-prompt-id A1 --max-iterations 5

# Lancement nuit (1020 cas)
python scripts/generate_golden_qa_v1.py \\
    --config config/diverse_prompts_50.yaml \\
    --output data/golden_qa/golden_qa_v1.jsonl \\
    --parallel 3 --target 1020 --model claude-opus-4-7
```
"""
from __future__ import annotations

import argparse
import json
import re
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ────────────────────────────── Constants ─────────────────────────────

DEFAULT_PARALLEL = 3
DEFAULT_RATE_LIMIT_DELAY = 0.5
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_S = 300
RATE_LIMIT_BACKOFF_BASE = 2.0
MAX_CONSECUTIVE_429 = 10  # stop condition

# Pivot 2026-05-02 (ordre Jarvis 1402 — Matteo Telegram 3053) : P3+P4
# fusion critique+refine passe d'Opus 4.7 → Sonnet 4.6 pour économie tokens
# sur le quota Claude Max plan partagé. Risque qualité accepté + audité
# empiriquement post-run. P1 (Haiku research) et P2 (Opus draft) inchangés
# — la créativité du draft reste user-facing top quality.
# Override possible via --model-critique-refine si rollback nécessaire.
DEFAULT_MODEL_CRITIQUE_REFINE = "claude-sonnet-4-6"

# Boundaries v3.1 (ordre 1011 nuit2-prep, recos Matteo review Phase 1) :
# keep ≥ 82 (vs 85 v3) — frontière 82-84 jugée trop sévère vu samples qualité.
# La nuit 1 a montré un cluster solide de 9 fiches scorées 78-84 ("flag")
# qui sont qualitativement similaires aux keep — Matteo recalibre +3 points.
SCORE_KEEP_THRESHOLD = 82
SCORE_FLAG_THRESHOLD = 70

# Détection 429 / rate limit / quota Claude Max plan dans stderr/stdout subprocess
# (la CLI `claude --print` peut exit en signalant des limites de plusieurs façons :
#  HTTP 429 standard, message "out of extra usage" Claude Max, "limit reached", etc.)
_RATE_LIMIT_PATTERNS = [
    re.compile(r"\brate[-_ ]?limit", re.IGNORECASE),
    re.compile(r"\b429\b"),
    re.compile(r"\bquota exceeded", re.IGNORECASE),
    re.compile(r"\btoo many requests", re.IGNORECASE),
    # Claude Max plan limits (signature observée 2026-04-28 dryrun v2 :
    # "You're out of extra usage · resets 5:40pm (Europe/Paris)")
    re.compile(r"\bout of (?:extra )?usage", re.IGNORECASE),
    re.compile(r"\busage limit", re.IGNORECASE),
    re.compile(r"\b(?:5-?hour|monthly) limit", re.IGNORECASE),
    re.compile(r"\bresets? (?:at )?\d", re.IGNORECASE),  # "resets 5:40pm" / "resets at 17h"
]

# Cap pour ne pas exploser la taille du JSONL
_RESEARCH_TEXT_CAP = 5000
_RAW_FALLBACK_CAP = 2000

# Global shutdown signal (CTRL+C clean)
_shutdown_event = threading.Event()


# ────────────────────────────── Datatypes ─────────────────────────────


@dataclass
class GenerateConfig:
    yaml_config_path: Path
    output_jsonl: Path
    parallel: int = DEFAULT_PARALLEL
    target: int | None = None
    filter_prompt_id: str | None = None
    max_iterations: int | None = None
    # Modèle global (legacy compat tests v1+v2). Si non-None ET les 3 flags
    # phase-specific en dessous restent à None, utilisé pour toutes les phases.
    model: str | None = None
    # Stratégie hybride v3 (Sprint 9-data Levier 1) — 3 modèles selon criticité
    # phase. Si None, fallback sur `model` (legacy) puis sur le default CLI
    # session côté `claude --print` (P1+P2) ou DEFAULT_MODEL_CRITIQUE_REFINE (P3+P4).
    # Phase 1 research WebSearch : recherche factuelle suffit, Haiku économique
    # Phase 2 draft : créativité conseiller user-facing → Opus qualité top
    # Phase 3+4 fusion critique+refine : Sonnet 4.6 par défaut depuis pivot
    # 2026-05-02 (économie tokens, cf DEFAULT_MODEL_CRITIQUE_REFINE)
    model_research: str | None = None
    model_draft: str | None = None
    model_critique_refine: str | None = None
    rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY
    max_retries: int = DEFAULT_MAX_RETRIES
    timeout_s: int = DEFAULT_TIMEOUT_S
    dry_run_no_subprocess: bool = False  # debug : no subprocess, fake responses
    # Mode drops-only nuit 2+ : si fourni, ne skip au resume QUE les records
    # dont decision ∈ skip_decisions. Permet de relancer uniquement les drops
    # (passer ["keep", "flag"]) sans perdre les valides nuit précédente.
    # None = comportement original (skip TOUT ce qui est dans le JSONL).
    skip_decisions: list[str] | None = None


@dataclass
class RetryStats:
    """Statistiques retries thread-safe pour stop conditions."""

    consecutive_429: int = 0
    total_429: int = 0
    total_success: int = 0
    total_other_errors: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_success(self) -> None:
        with self._lock:
            self.consecutive_429 = 0
            self.total_success += 1

    def record_429(self) -> int:
        with self._lock:
            self.consecutive_429 += 1
            self.total_429 += 1
            return self.consecutive_429

    def record_other_error(self) -> None:
        with self._lock:
            self.total_other_errors += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "success": self.total_success,
                "429": self.total_429,
                "other_errors": self.total_other_errors,
                "consecutive_429": self.consecutive_429,
            }


# ────────────────────────────── Subprocess wrapper ──────────────────────


def call_claude_subprocess(
    prompt: str,
    allowed_tools: list[str] | None = None,
    model: str | None = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> tuple[str, str, int]:
    """Invoque `claude --print` subprocess. Retourne (stdout, stderr, returncode)."""
    cmd = ["claude", "--print"]
    if allowed_tools:
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])
    if model:
        cmd.extend(["--model", model])
    cmd.append(prompt)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", f"timeout after {timeout_s}s", -1
    except FileNotFoundError:
        return "", "claude CLI not found in PATH (install Claude Code first)", -2


def is_rate_limit_error(stderr: str, stdout: str) -> bool:
    """Détecte 429 / rate limit dans stderr ou stdout."""
    for text in (stderr or "", stdout or ""):
        for pattern in _RATE_LIMIT_PATTERNS:
            if pattern.search(text):
                return True
    return False


def call_claude_with_retry(
    prompt: str,
    cfg: GenerateConfig,
    retry_stats: RetryStats,
    allowed_tools: list[str] | None = None,
    model: str | None = None,
) -> str:
    """Subprocess avec backoff exponentiel sur 429. Raise RuntimeError sur fail définitif.

    Le `model` arg explicite (Sprint 9-data v3 stratégie hybride) override le
    `cfg.model` legacy. Permet d'utiliser un modèle phase-specific sans casser
    la compat tests v1+v2 qui passent uniquement par cfg.model.
    """
    if cfg.dry_run_no_subprocess:
        return _fake_response_for_debug(prompt)

    effective_model = model if model is not None else cfg.model

    for attempt in range(cfg.max_retries + 1):
        if _shutdown_event.is_set():
            raise RuntimeError("shutdown signal received")

        stdout, stderr, rc = call_claude_subprocess(
            prompt,
            allowed_tools=allowed_tools,
            model=effective_model,
            timeout_s=cfg.timeout_s,
        )

        if rc == 0 and stdout:
            retry_stats.record_success()
            time.sleep(cfg.rate_limit_delay)
            return stdout

        if is_rate_limit_error(stderr, stdout):
            consecutive = retry_stats.record_429()
            if consecutive > MAX_CONSECUTIVE_429:
                # Set d'abord, raise ensuite : l'event est l'autorité d'arrêt
                # thread-safe (visible par tous les workers du pool dès leur
                # prochaine itération ligne ~238). L'exception peut être
                # absorbée par un try/except parent — l'event, lui, ne peut
                # pas être "oublié" silencieusement (cf bug nuit 28-29 : 975
                # drops parce que generate_qa avalait le RuntimeError).
                _shutdown_event.set()
                raise RuntimeError(
                    f"Stop condition: {consecutive} consecutive 429 — abort "
                    "(reduce --parallel or wait Claude Max quota reset)"
                )
            backoff = (RATE_LIMIT_BACKOFF_BASE ** attempt) + cfg.rate_limit_delay
            time.sleep(backoff)
            continue

        # Autre erreur (timeout, CLI not found, malformed prompt)
        retry_stats.record_other_error()
        if attempt < cfg.max_retries:
            time.sleep(cfg.rate_limit_delay * (attempt + 1))
            continue
        raise RuntimeError(
            f"claude --print failed after {cfg.max_retries} retries "
            f"(rc={rc}): {(stderr or stdout)[:500]}"
        )

    raise RuntimeError("call_claude_with_retry: unreachable (loop exhausted)")


def _fake_response_for_debug(prompt: str) -> str:
    """Réponse fake pour mode debug `--dry-run-no-subprocess` (CI / tests).

    Détection par schema attendu dans le prompt (markers "Output JSON STRICT")
    plutôt que par mots-clés du contenu, pour éviter les faux-positifs (ex
    Phase 2 prompt mentionnant 'Phase 1' dans une instruction).
    """
    # v3 fusion Phase 3+4 : prompt contient ET score_total ET answer_refined
    # → return un objet unifié (priorité haute, check en premier)
    has_score = '"score_total"' in prompt and '"scores_par_axe"' in prompt
    has_answer_refined = '"answer_refined"' in prompt
    has_qa_pair = (
        '"question"' in prompt and '"answer"' in prompt and not has_answer_refined
    )

    if has_score and has_answer_refined:
        # v3 fusion critique+refine — output combiné
        return (
            '{"score_total": 90, "scores_par_axe": {"factuelle": 22, "posture": 23, '
            '"coherence": 23, "hallucination": 22}, "corrections_suggérées": "RAS — fake debug v3 fusion", '
            '"decision_recommandée": "keep", "question": "Q fake refined", '
            '"answer_refined": "A fake refined v3 fusion"}'
        )
    if has_score:
        # v1+v2 critique standalone (legacy compat tests)
        return '{"score_total": 90, "scores_par_axe": {"factuelle": 22, "posture": 23, "coherence": 23, "hallucination": 22}, "corrections_suggérées": "RAS — fake debug", "decision_recommandée": "keep"}'
    if has_answer_refined:
        return '{"question": "Q fake", "answer_refined": "A fake refined"}'
    if has_qa_pair:
        return '{"question": "Q fake", "answer": "A fake draft"}'
    # Phase 1 research : output plain text, pas de schema JSON attendu
    return "- URL: https://example.gouv.fr\n- Date: 2026-01-15\n- Extrait clé: Source factice."


# ────────────────────────────── 4-phase pipeline ────────────────────────


class Phase1Cache:
    """Cache thread-safe Phase 1 research par `prompt_id` (Sprint 9-data v3 Levier 2).

    51 prompts × 20 itérations = 1020 calls Phase 1 sans cache. Avec cache
    par prompt_id (research factuel stable pour un persona donné), seul le
    premier hit fait l'appel. **-969 calls économisés**.

    Pattern double-checked locking : compute en dehors du lock pour ne pas
    bloquer les autres threads pendant le research (~30s). Tolère 1 race
    de double-compute par prompt_id par session (max 51 doubles, négligeable
    vs gain). Le 2nd compute est jeté, le premier reste cached.
    """

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}
        self._lock = threading.Lock()

    def get(self, prompt_id: str) -> str | None:
        with self._lock:
            return self._cache.get(prompt_id)

    def get_or_compute(self, prompt_id: str, compute_fn) -> tuple[str, bool]:
        """Retourne (research_text, cache_hit_bool).

        cache_hit=True si retourné depuis cache (skip compute).
        cache_hit=False si compute_fn vient d'être appelée et résultat stocké.
        """
        with self._lock:
            cached = self._cache.get(prompt_id)
            if cached is not None:
                return cached, True
        # Compute hors lock pour ne pas bloquer
        result = compute_fn()
        with self._lock:
            existing = self._cache.get(prompt_id)
            if existing is not None:
                # Race condition tolérée : un autre thread a écrit en parallèle.
                # On garde le premier (existing), on jette `result`.
                return existing, True
            self._cache[prompt_id] = result
            return result, False

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


def phase1_research(
    prompt_config: dict,
    cfg: GenerateConfig,
    retry_stats: RetryStats,
    cache: Phase1Cache | None = None,
) -> tuple[str, bool]:
    """Phase 1 research avec cache optionnel par prompt_id.

    Si `cache` est None, ancien comportement (call à chaque iter).
    Si `cache` est fourni, lookup d'abord, compute miss only.

    Returns:
        (research_text, cache_hit) — cache_hit=True si skipped via cache.
    """
    sources_str = "\n  - ".join(prompt_config["sources_priority"])
    prompt = f"""Pour ce persona : {prompt_config['persona']}
Et ce contexte : {prompt_config['context']}

Cherche les dernières infos officielles 2025-2026 via WebSearch.

Sources à prioriser (utilise WebSearch sur ces domaines en priorité) :
  - {sources_str}

Output : 3-5 sources factuelles datées, chaque source au format :
- URL : ...
- Date : ... (préfère 2025-2026)
- Extrait clé : ... (1-2 phrases factuelles)

Réponds UNIQUEMENT avec ces sources, pas de préambule, pas de markdown autour."""

    def _compute() -> str:
        return call_claude_with_retry(
            prompt,
            cfg,
            retry_stats,
            allowed_tools=["WebSearch", "WebFetch"],
            model=cfg.model_research or cfg.model,
        )

    if cache is None:
        return _compute(), False

    return cache.get_or_compute(prompt_config["id"], _compute)


def phase2_draft(
    prompt_config: dict,
    research_result: str,
    question_seed: str,
    cfg: GenerateConfig,
    retry_stats: RetryStats,
) -> str:
    prompt = f"""Tu es un expert orientation conseiller bienveillant. Avec ces sources factuelles :

{research_result}

Et ce contexte profil :
- Persona : {prompt_config['persona']}
- Context : {prompt_config['context']}
- Constraints : {prompt_config['constraints']}
- Tone : {prompt_config['tone']}

Génère 1 Q&A type entretien d'orientation.

QUESTION (à varier autour de la seed mais en restant proche de l'esprit du seed) :
"{question_seed}"

RÉPONSE PARFAITE de conseiller bienveillant :
- Active listening + reformulation en ouverture (1-2 phrases "Si je te/vous comprends bien...")
- Reconnaissance émotion si pertinent (1 phrase max, optionnel)
- 3 pistes pondérées non-prescriptives avec critères objectifs (durée, coût, sélectivité, débouché)
- INTERDIT : reco prescriptive ("tu devrais"). Toujours 3 options pondérées
- Question finale d'exploration qui rend le choix à l'utilisateur·ice
- Tone strictement {prompt_config['tone']}

⚠️ RÈGLE ABSOLUE ANTI-HALLUCINATION CHIFFRÉE (v3.1) ⚠️

JAMAIS DE CHIFFRES PRÉCIS NON SOURCÉS PHASE 1 RESEARCH.

EXEMPLES STRICTEMENT INTERDITS sans source explicite Phase 1 :
- DATES DE CONCOURS PRÉCISES (ex "écrits avril 2026", "résultats juin 2026")
- NOMBRES DE PLACES (ex "150 places", "promo de 30")
- TAUX D'ADMISSION/SÉLECTIVITÉ EN % (ex "28% sélectivité", "1 sur 4")
- COÛTS PRÉCIS EN € (ex "10 500€/an", "1 200€/mois")
- DURÉES PRÉCISES (ex "9 mois de césure", "stage de 6 semaines")
- TAUX D'INSERTION EN % (ex "90% insertion à 6 mois", "85% en CDI")
- SALAIRES PRÉCIS (ex "2 000€ brut", "moyenne 35k€")

TERMES QUALITATIFS OBLIGATOIRES en remplacement :
- "écrits avril 2026" → "au printemps" / "en fin d'année scolaire"
- "150 places" → "places limitées" / "promotion réduite"
- "28% sélectif" → "très sélectif" / "sélectivité modérée"
- "10 500€/an" → "frais élevés (école privée de commerce)"
- "9 mois de césure" → "césure de quelques mois à 1 an"
- "90% insertion" → "très bonne insertion documentée"
- "salaire moyen 2 000€" → "salaire de débutant standard"

INTERDICTION STRICTE de chiffres précis (tarif, salaire, %, durée, taux d'insertion, sélectivité, places concours, années, mensualité, montant aide, score moyen) non EXPLICITEMENT présents dans les sources de la Phase 1 WebSearch.

NE JAMAIS écrire un nombre (avec %, €, ans, mois, mensuel, points, places, etc.) sans vérifier qu'il est dans le research Phase 1. En cas de doute, **registre qualitatif obligatoire**.

Cette règle est plus stricte que l'ancien estimation marker : on retire complètement les chiffres non sourcés au lieu de les flagger "(estimation)". Raison : Mistral en inférence finale peut perdre le marker `(estimation)` et propager des faux chiffres en confiance — éviter le risque à la racine.

Vérifie chaque chiffre dans ta réponse : est-il textuellement dans le research Phase 1 ci-dessus ? Si NON → remplace par formulation qualitative.

LISIBILITÉ MOBILE OBLIGATOIRE :
- Lecteur cible : 17-25 ans sur smartphone, souvent angoissé (Parcoursup, réorientation)
- Format obligatoire :
  - 1-2 phrases reformulation/active listening en ouverture
  - 3 pistes en BULLET POINTS COURTS (max 2-3 phrases par piste, pas de paragraphe long)
  - 1 phrase question finale d'exploration
- Limite totale : **250-350 mots maximum**
- Sauts de ligne entre pistes pour respiration
- Densité = ennemi du lecteur stressé. Bloc texte massif INTERDIT.

Output JSON STRICT :
{{
  "question": "...",
  "answer": "..."
}}

Réponds UNIQUEMENT avec ce JSON, pas de préambule, pas de markdown autour."""
    return call_claude_with_retry(prompt, cfg, retry_stats, model=cfg.model_draft or cfg.model)


def phase34_critique_refine(
    draft_raw: str,
    prompt_config: dict,
    cfg: GenerateConfig,
    retry_stats: RetryStats,
) -> str:
    """Sprint 9-data v3 Levier 3 — fusion Phase 3 (critique 4 axes) + Phase 4
    (refine intégrant corrections) en 1 seul call → -1020 calls vs pipeline
    4 phases séparées.

    Le LLM produit en 1 output JSON unique :
    - scores_par_axe + score_total (rôle Phase 3)
    - corrections_suggérées + decision_recommandée (rôle Phase 3)
    - answer_refined avec corrections appliquées (rôle Phase 4)

    Trade-off : un seul prompt doit faire 2 jobs (évaluer + réécrire). Plus
    long contextuel mais 1 appel au lieu de 2. Net usage budget économique.
    """
    prompt = f"""Tu es À LA FOIS évaluateur qualité Q&A orientation ET expert orientation. Tu fais 2 choses dans le MÊME output :

1. Évaluer la Q&A draft sur 4 axes /25 chacun (total /100)
2. Réécrire la réponse en intégrant tes propres corrections suggérées

DRAFT À ÉVALUER ET RÉÉCRIRE :

{draft_raw}

Profil cible attendu :
- Persona : {prompt_config['persona']}
- Tone attendu : {prompt_config['tone']}

## Étape 1 — Évaluation 4 axes /25 (total /100)

1. Pertinence factuelle (formation existe vraiment, infos justes, pas de chiffre inventé hors sources) /25
2. Posture conseiller (questions ouvertes, non-jugement, reformulation présente, 3 options pondérées non-prescriptives) /25
3. Cohérence avec persona/contexte (vocabulaire/registre adapté au tone, contraintes respectées) /25
4. Absence d'hallucination flagrante (pas de slug ONISEP/Parcoursup inventé, pas d'URL bidon, pas d'école inexistante, pas de chiffre précis non sourcé) /25

Pénalités lourdes (-10 sur l'axe correspondant) :
- "Tu devrais faire X" (prescriptif au lieu de pondéré)
- Reco au tour 1 sans questionnement préalable
- Slug ONISEP/Parcoursup factice
- Tone mismatch (ex: vouvoiement attendu, tutoiement produit)

## Étape 2 — Réécriture corrigée

Réécris la réponse en intégrant TOUTES les corrections suggérées que tu identifies. Préserve la question originale (ne pas la modifier). Préserve le ton et la structure conseiller (reformulation + 3 options pondérées + question finale).

Si la draft est déjà excellente (score >=90), réécris-la quand même (légères variations pour normaliser le style) plutôt que de la copier.

## Output JSON STRICT (1 SEUL objet, pas de markdown autour)

{{
  "score_total": <int 0-100>,
  "scores_par_axe": {{
    "factuelle": <int 0-25>,
    "posture": <int 0-25>,
    "coherence": <int 0-25>,
    "hallucination": <int 0-25>
  }},
  "corrections_suggérées": "<text 1-3 phrases courtes — ce que tu as corrigé>",
  "decision_recommandée": "<keep|flag|drop>",
  "question": "<question préservée du draft>",
  "answer_refined": "<réponse réécrite avec corrections appliquées>"
}}

Réponds UNIQUEMENT avec ce JSON, pas de préambule."""
    return call_claude_with_retry(
        prompt, cfg, retry_stats,
        model=cfg.model_critique_refine or cfg.model or DEFAULT_MODEL_CRITIQUE_REFINE,
    )


# ────────────────────────────── JSONL appender ─────────────────────────


class ThreadSafeJsonlAppender:
    """Append JSON lines à un fichier en mode thread-safe.

    Pattern reproduit de `src/agent/parallel.py:parallel_apply` Sprint 4-5.
    Chaque write est atomique (lock + open(append) + write + close).
    """

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def append(self, record: dict) -> None:
        line = json.dumps(record, ensure_ascii=False)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def existing_keys(self, skip_decisions: list[str] | None = None) -> set[tuple]:
        """Retourne l'ensemble des (prompt_id, iteration) déjà présents.

        Utilisé pour le checkpointing : skip les jobs déjà faits au resume.
        Tolère les lignes JSON invalides (skip silencieusement, log).

        Args:
            skip_decisions: si fourni, ne retient dans l'ensemble que les records
                dont `decision` ∈ skip_decisions. Permet le mode drops-only nuit 2+ :
                passer ["keep", "flag"] = skip uniquement les valides, refait les drops.
                Default None = comportement original (skip TOUT ce qui est dans le JSONL).
        """
        keys: set[tuple] = set()
        if not self.path.exists() or self.path.stat().st_size == 0:
            return keys
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if skip_decisions is not None:
                        if rec.get("decision") not in skip_decisions:
                            continue
                    keys.add((rec.get("prompt_id"), rec.get("iteration")))
                except json.JSONDecodeError:
                    continue
        return keys


# ────────────────────────────── Decision policy + parsing ───────────────


def decision_from_score(score: int) -> str:
    if score >= SCORE_KEEP_THRESHOLD:
        return "keep"
    if score >= SCORE_FLAG_THRESHOLD:
        return "flag"
    return "drop"


def parse_json_safe(text: str) -> dict | None:
    """Parse JSON robuste — tolère ```json blocks, préambules courts, JSON imbriqué."""
    if not text:
        return None
    text = text.strip()
    # Strip markdown json fence
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback : regex extraction du premier { ... } objet
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


# ────────────────────────────── Main 4-phase orchestration ─────────────


def generate_qa(
    prompt_config: dict,
    iteration_idx: int,
    cfg: GenerateConfig,
    retry_stats: RetryStats,
    phase1_cache: Phase1Cache | None = None,
) -> dict:
    """Orchestre les phases pour 1 (prompt_id, iteration_idx).

    v3 stratégie hybride (Sprint 9-data) + pivot 2026-05-02 :
    - Phase 1 research : Haiku 4.5 (cfg.model_research) + cache par prompt_id
    - Phase 2 draft : Opus 4.7 (cfg.model_draft)
    - Phase 3+4 fusion (critique + refine) : Sonnet 4.6 par défaut depuis le
      pivot 2026-05-02 (DEFAULT_MODEL_CRITIQUE_REFINE) — économie tokens.
      Override possible via cfg.model_critique_refine.

    Si `phase1_cache` est None, ancien comportement (call à chaque iter).
    """
    t0 = time.time()
    seeds = prompt_config["questions_seed"]
    question_seed = seeds[iteration_idx % len(seeds)]

    record: dict[str, Any] = {
        "prompt_id": prompt_config["id"],
        "iteration": iteration_idx,
        "question_seed": question_seed,
        "category": prompt_config["category"],
        "axe_couvert": prompt_config["axe_couvert"],
        "models": {
            "research": cfg.model_research or cfg.model,
            "draft": cfg.model_draft or cfg.model,
            "critique_refine": (
                cfg.model_critique_refine or cfg.model or DEFAULT_MODEL_CRITIQUE_REFINE
            ),
        },
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    try:
        # Phase 1 — Research WebSearch (avec cache prompt_id si fourni)
        research, cache_hit = phase1_research(prompt_config, cfg, retry_stats, phase1_cache)
        record["research_cache_hit"] = cache_hit

        # Phase 2 — Draft persona conseiller
        draft_raw = phase2_draft(prompt_config, research, question_seed, cfg, retry_stats)
        draft = parse_json_safe(draft_raw)

        # Phase 3+4 fusion — critique 4 axes + refine en 1 call
        cr_raw = phase34_critique_refine(draft_raw, prompt_config, cfg, retry_stats)
        cr = parse_json_safe(cr_raw)
        score = int(cr.get("score_total", 0)) if cr else 0

        # Extraction des 2 sous-objets pour préserver le schema JSONL existant
        # (compat tools et tests qui lisent record["critique"] et record["final_qa"])
        if cr:
            critique = {
                "score_total": cr.get("score_total"),
                "scores_par_axe": cr.get("scores_par_axe"),
                "corrections_suggérées": cr.get("corrections_suggérées"),
                "decision_recommandée": cr.get("decision_recommandée"),
            }
            final_qa = {
                "question": cr.get("question"),
                "answer_refined": cr.get("answer_refined"),
            }
        else:
            critique = {"raw": cr_raw[:_RAW_FALLBACK_CAP]}
            final_qa = {"raw": cr_raw[:_RAW_FALLBACK_CAP]}

        record.update({
            "research_sources_text": research[:_RESEARCH_TEXT_CAP],
            "draft": draft or {"raw": draft_raw[:_RAW_FALLBACK_CAP]},
            "critique": critique,
            "final_qa": final_qa,
            "score_total": score,
            "decision": decision_from_score(score),
            "elapsed_s": round(time.time() - t0, 1),
            "error": None,
        })
    except Exception as e:
        # Defense in depth : les RuntimeError "Stop condition" levées par
        # call_claude_with_retry doivent remonter (pas être absorbées en
        # record drop). Le set _shutdown_event côté call_claude_with_retry
        # reste l'autorité primaire — ce filtre est belt & suspenders pour
        # garantir que la stack trace remonte au main loop, lequel break
        # la boucle as_completed et appelle pool.shutdown(cancel_futures=True).
        if isinstance(e, RuntimeError) and "Stop condition" in str(e):
            raise
        record.update({
            "error": f"{type(e).__name__}: {e}",
            "decision": "drop",
            "score_total": 0,
            "elapsed_s": round(time.time() - t0, 1),
        })
    return record


# ────────────────────────────── CLI / main ──────────────────────────────


def parse_cli() -> GenerateConfig:
    p = argparse.ArgumentParser(
        description="Pipeline agentique 4 phases — génération 1000 Q&A conseiller"
    )
    p.add_argument("--config", type=Path, required=True, help="YAML config 51 prompts")
    p.add_argument("--output", type=Path, required=True, help="Output JSONL append-only")
    p.add_argument("--parallel", type=int, default=DEFAULT_PARALLEL,
                   help=f"Sub-agents simultanés (défaut {DEFAULT_PARALLEL}). "
                        "Max 20x: 5, Max 5x: 2, Pro: 1")
    p.add_argument("--target", type=int, default=None,
                   help="Cap nb total Q&A à générer (défaut : tous prompts × max_iterations)")
    p.add_argument("--filter-prompt-id", type=str, default=None,
                   help="Filtre sur 1 seul prompt (pour dry-run, ex: A1)")
    p.add_argument("--max-iterations", type=int, default=None,
                   help="Override iterations_per_prompt YAML metadata")
    p.add_argument("--model", type=str, default=None,
                   help="Modèle Claude global (legacy v1+v2). claude-opus-4-7 / opus-4.7 / drop pour default. "
                        "Override par --model-research / --model-draft / --model-critique-refine si fournis.")
    # Stratégie hybride v3 (Sprint 9-data Levier 1) — 3 modèles selon criticité
    p.add_argument("--model-research", type=str, default=None,
                   help="Modèle Phase 1 research WebSearch (v3 stratégie hybride). "
                        "Recherche factuelle suffit, défault Haiku (économie usage). "
                        "Ex : claude-haiku-4-5")
    p.add_argument("--model-draft", type=str, default=None,
                   help="Modèle Phase 2 draft persona conseiller (v3 stratégie hybride). "
                        "Créativité conseiller user-facing, défault Opus (qualité top). "
                        "Ex : claude-opus-4-7")
    p.add_argument("--model-critique-refine", type=str, default=None,
                   help="Modèle Phase 3+4 fusion critique+refine (v3 stratégie hybride). "
                        "Défaut DEFAULT_MODEL_CRITIQUE_REFINE = claude-sonnet-4-6 "
                        "depuis pivot 2026-05-02 (économie tokens). "
                        "Override Opus rollback : --model-critique-refine claude-opus-4-7")
    p.add_argument("--rate-limit-delay", type=float, default=DEFAULT_RATE_LIMIT_DELAY,
                   help=f"Délai entre calls subprocess (s, défaut {DEFAULT_RATE_LIMIT_DELAY})")
    p.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES,
                   help=f"Retries sur 429 (défaut {DEFAULT_MAX_RETRIES})")
    p.add_argument("--timeout-s", type=int, default=DEFAULT_TIMEOUT_S,
                   help=f"Timeout subprocess (s, défaut {DEFAULT_TIMEOUT_S})")
    p.add_argument("--dry-run-no-subprocess", action="store_true",
                   help="Debug : remplace subprocess par fake responses (no API)")
    p.add_argument("--skip-decisions", type=str, default=None,
                   help="Liste séparée par virgule des decisions à skip au resume "
                        "(ex 'keep,flag'). Mode drops-only nuit 2+ : permet de "
                        "relancer uniquement les drops sans perdre les valides "
                        "des runs précédents. Default = skip TOUT ce qui est dans le JSONL.")
    args = p.parse_args()
    skip_decisions = None
    if args.skip_decisions:
        skip_decisions = [d.strip() for d in args.skip_decisions.split(",") if d.strip()]

    return GenerateConfig(
        yaml_config_path=args.config,
        output_jsonl=args.output,
        parallel=args.parallel,
        target=args.target,
        filter_prompt_id=args.filter_prompt_id,
        max_iterations=args.max_iterations,
        model=args.model,
        model_research=args.model_research,
        model_draft=args.model_draft,
        model_critique_refine=args.model_critique_refine,
        rate_limit_delay=args.rate_limit_delay,
        max_retries=args.max_retries,
        timeout_s=args.timeout_s,
        dry_run_no_subprocess=args.dry_run_no_subprocess,
        skip_decisions=skip_decisions,
    )


def _signal_handler(signum, _frame):
    print(f"\n⚠️  Signal {signum} reçu — arrêt propre en cours (en attente fin des tâches en vol)...",
          flush=True)
    _shutdown_event.set()


def build_jobs(yaml_data: dict, cfg: GenerateConfig) -> list[tuple[dict, int]]:
    """Construit la liste des jobs (prompt_config, iteration_idx)."""
    prompts = yaml_data["prompts"]
    if cfg.filter_prompt_id:
        prompts = [p for p in prompts if p["id"] == cfg.filter_prompt_id]
        if not prompts:
            raise ValueError(f"Aucun prompt trouvé pour --filter-prompt-id {cfg.filter_prompt_id}")
    iter_per_prompt = (
        cfg.max_iterations
        or yaml_data.get("metadata", {}).get("iterations_per_prompt", 20)
    )
    jobs = [(p, i) for p in prompts for i in range(iter_per_prompt)]
    if cfg.target:
        jobs = jobs[: cfg.target]
    return jobs


def run_pipeline(
    cfg: GenerateConfig,
    jobs_to_run: list[tuple[dict, int]],
    appender: "ThreadSafeJsonlAppender",
) -> int:
    """Boucle d'exécution principale (extrait de main() pour testabilité).

    Exit codes :
    - 0 : succès normal
    - 2 : error_rate > 30% (signal investigation)
    - 3 : shutdown event détecté pendant l'exécution (signal arrêt brutal :
          quota grillé, SIGINT/SIGTERM, ou stop condition consecutive 429)
    """
    if not jobs_to_run:
        print("==> Rien à faire (tous les jobs déjà présents dans le JSONL).")
        return 0

    retry_stats = RetryStats()
    phase1_cache = Phase1Cache()  # v3 Levier 2 — cache research par prompt_id
    counts: dict[str, int] = {"keep": 0, "flag": 0, "drop": 0}
    errors_count = 0
    t_start = time.time()

    with ThreadPoolExecutor(max_workers=cfg.parallel) as pool:
        futures = {
            pool.submit(generate_qa, pc, ii, cfg, retry_stats, phase1_cache): (pc["id"], ii)
            for pc, ii in jobs_to_run
        }

        for i, fut in enumerate(as_completed(futures), 1):
            if _shutdown_event.is_set():
                pool.shutdown(wait=False, cancel_futures=True)
                print("\n==> Shutdown propagé, arrêt des futures restantes.")
                break
            try:
                rec = fut.result()
            except Exception as e:
                errors_count += 1
                # Si stop condition détectée via exception remontée par
                # generate_qa (defense in depth #2), set l'event pour que
                # l'itération suivante break proprement.
                if isinstance(e, RuntimeError) and "Stop condition" in str(e):
                    _shutdown_event.set()
                print(f"[{i}/{len(jobs_to_run)}] ERROR future: {type(e).__name__}: {e}",
                      flush=True)
                continue

            appender.append(rec)
            decision = rec.get("decision", "drop")
            counts[decision] = counts.get(decision, 0) + 1
            if rec.get("error"):
                errors_count += 1

            if i % 10 == 0 or i == len(jobs_to_run) or i <= 5:
                elapsed = time.time() - t_start
                rate = i / elapsed if elapsed > 0 else 0.0
                stats = retry_stats.snapshot()
                print(f"[{i}/{len(jobs_to_run)}] {rec['prompt_id']}#{rec['iteration']} → "
                      f"{decision} (score={rec.get('score_total', 0)}) | "
                      f"counts={counts} errors={errors_count} | "
                      f"rate={rate:.2f}/s | retry={stats}",
                      flush=True)

    total_elapsed = time.time() - t_start
    print(f"\n==> DONE. Elapsed: {total_elapsed/60:.1f} min")
    print(f"    Final counts: {counts}, errors: {errors_count}")
    print(f"    Retry stats: {retry_stats.snapshot()}")

    if _shutdown_event.is_set():
        print("⚠️  Shutdown event détecté — arrêt brutal (quota grillé, "
              "SIGINT/SIGTERM, ou stop condition consecutive 429).")
        return 3
    error_rate = errors_count / max(len(jobs_to_run), 1)
    if error_rate > 0.30:
        print(f"⚠️  Error rate {error_rate:.1%} > 30% — investigation requise.")
        return 2
    return 0


def main() -> int:
    cfg = parse_cli()
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    print(f"==> generate_golden_qa_v1.py")
    print(f"    config: {cfg.yaml_config_path}")
    print(f"    output: {cfg.output_jsonl}")
    print(f"    parallel: {cfg.parallel}, rate_limit_delay: {cfg.rate_limit_delay}s, "
          f"max_retries: {cfg.max_retries}")
    print(f"    models: research={cfg.model_research or cfg.model or '(default)'} | "
          f"draft={cfg.model_draft or cfg.model or '(default)'} | "
          f"critique-refine={cfg.model_critique_refine or cfg.model or '(default)'}")
    if cfg.dry_run_no_subprocess:
        print("    ⚠️  --dry-run-no-subprocess : NO real subprocess, fake responses")

    yaml_data = yaml.safe_load(cfg.yaml_config_path.read_text(encoding="utf-8"))
    jobs = build_jobs(yaml_data, cfg)

    appender = ThreadSafeJsonlAppender(cfg.output_jsonl)
    existing = appender.existing_keys(skip_decisions=cfg.skip_decisions)
    jobs_to_run = [(p, i) for p, i in jobs if (p["id"], i) not in existing]

    if cfg.skip_decisions is not None:
        print(f"    🌙 Mode drops-only : skip uniquement decisions ∈ {cfg.skip_decisions}")
    print(f"    jobs total: {len(jobs)}, déjà fait (skip): {len(existing)}, à exécuter: {len(jobs_to_run)}")

    return run_pipeline(cfg, jobs_to_run, appender)


if __name__ == "__main__":
    sys.exit(main())
