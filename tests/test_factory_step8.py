"""Tests step 8 — flag enable_router_llm + helper router_llm_artifacts_present.

Couvre :
- make_production_pipeline avec router activé par défaut → pipeline.router_llm défini
- make_production_pipeline avec enable_router_llm=False → pipeline.router_llm=None
- Le RouterLLM utilise le MÊME client Mistral que le pipeline (audit step 7 → 8)
- router_model param est respecté
- Helper router_llm_artifacts_present retourne True/False selon présence
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.rag.factory import (
    DEFAULT_QUAD_GROUP_NAMES,
    make_production_pipeline,
    router_llm_artifacts_present,
)
from src.rag.router_llm import RouterLLM


# ────────────────────────── make_production_pipeline ──────────────────────────


def test_factory_default_enables_router_llm() -> None:
    """Default : enable_router_llm=True → pipeline.router_llm est instancié."""
    client = MagicMock()
    fiches = [{"id": "t-0", "nom": "Test"}]
    pipeline = make_production_pipeline(client, fiches)
    assert pipeline.router_llm is not None
    assert isinstance(pipeline.router_llm, RouterLLM)


def test_factory_disabled_router_llm_keeps_pipeline_baseline() -> None:
    """enable_router_llm=False → pipeline.router_llm=None (préserve Run F+G)."""
    client = MagicMock()
    fiches = [{"id": "t-0", "nom": "Test"}]
    pipeline = make_production_pipeline(client, fiches, enable_router_llm=False)
    assert pipeline.router_llm is None


def test_factory_router_uses_same_client_as_pipeline() -> None:
    """CRUCIAL (audit step 7 → 8) : le RouterLLM réutilise le client
    Mistral du pipeline. Pas de double instanciation = un seul session
    rate-limit + un seul cache hit."""
    client = MagicMock()
    fiches = [{"id": "t-0", "nom": "Test"}]
    pipeline = make_production_pipeline(client, fiches, enable_router_llm=True)
    assert pipeline.router_llm.client is client
    assert pipeline.client is client


def test_factory_router_model_default_is_mistral_small() -> None:
    """Default router_model = pin MISTRAL_SMALL (souverain léger, H1 lot 1.5)."""
    client = MagicMock()
    pipeline = make_production_pipeline(client, [{"id": "x"}])
    from src.rag.models import MISTRAL_SMALL
    assert pipeline.router_llm.model == MISTRAL_SMALL


def test_factory_router_model_can_be_overridden() -> None:
    """router_model param est propagé à RouterLLM."""
    client = MagicMock()
    pipeline = make_production_pipeline(
        client, [{"id": "x"}], router_model="mistral-medium-latest"
    )
    assert pipeline.router_llm.model == "mistral-medium-latest"


def test_factory_other_flags_independent_of_router() -> None:
    """enable_router_llm n'affecte pas les autres composants (Validator,
    ScopeClassifier, Golden QA, etc.)."""
    client = MagicMock()
    pipeline = make_production_pipeline(
        client, [{"id": "x"}], enable_router_llm=False, enable_validator=True,
    )
    assert pipeline.router_llm is None
    assert pipeline.validator is not None  # Validator pas affecté


# ────────────────────────── router_llm_artifacts_present ──────────────────────────


def test_artifacts_present_returns_false_if_manifest_missing(tmp_path: Path) -> None:
    """Manifest absent → False (caller fera rebuild en mémoire)."""
    fake_path = tmp_path / "no_such_manifest.json"
    assert router_llm_artifacts_present(manifest_path=str(fake_path)) is False


def test_artifacts_present_returns_false_if_manifest_invalid_json(tmp_path: Path) -> None:
    """Manifest présent mais JSON cassé → False (graceful)."""
    bad_path = tmp_path / "bad_manifest.json"
    bad_path.write_text("{not valid json", encoding="utf-8")
    assert router_llm_artifacts_present(manifest_path=str(bad_path)) is False


def test_artifacts_present_returns_false_if_groups_mismatch(tmp_path: Path) -> None:
    """Manifest avec mauvais ensemble de groupes → False."""
    manifest = {
        "version": "v7_quad_index",
        "groups": {
            "wrong_group": {"path": "data/embeddings/wrong.index"},
        },
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    assert router_llm_artifacts_present(manifest_path=str(p)) is False


def test_artifacts_present_returns_false_if_subindex_files_missing(tmp_path: Path) -> None:
    """Manifest référence des sub-indexes inexistants → False."""
    embeddings_dir = tmp_path / "data" / "embeddings"
    embeddings_dir.mkdir(parents=True)
    manifest = {
        "version": "v7_quad_index",
        "groups": {
            name: {"path": f"data/embeddings/formations_v7_{name}.index"}
            for name in DEFAULT_QUAD_GROUP_NAMES
        },
    }
    p = embeddings_dir / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    # Les 4 fichiers .index n'existent pas
    assert router_llm_artifacts_present(manifest_path=str(p)) is False


def test_artifacts_present_returns_true_when_all_present(tmp_path: Path) -> None:
    """Manifest valide + 4 fichiers .index présents → True."""
    embeddings_dir = tmp_path / "data" / "embeddings"
    embeddings_dir.mkdir(parents=True)
    # Crée 4 stub files (contenu non-importé par le helper, juste l'existence)
    for name in DEFAULT_QUAD_GROUP_NAMES:
        (embeddings_dir / f"formations_v7_{name}.index").write_bytes(b"stub")
    manifest = {
        "version": "v7_quad_index",
        "groups": {
            name: {"path": f"data/embeddings/formations_v7_{name}.index"}
            for name in DEFAULT_QUAD_GROUP_NAMES
        },
    }
    p = embeddings_dir / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    assert router_llm_artifacts_present(manifest_path=str(p)) is True


def test_artifacts_present_real_repo_artifacts() -> None:
    """Le manifest réel du repo (build au step 4) doit retourner True."""
    # Vérifie que les artefacts buildés au step 4 existent toujours.
    # Ne fail pas si le repo a été nettoyé (test informatif).
    repo_manifest = (
        Path(__file__).resolve().parents[1]
        / "data" / "embeddings" / "formations_partition_manifest.json"
    )
    if not repo_manifest.exists():
        pytest.skip("Sub-indexes pas buildés (run scripts/build_quad_subindexes.py)")
    assert router_llm_artifacts_present(manifest_path=str(repo_manifest)) is True
