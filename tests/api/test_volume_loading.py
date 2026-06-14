"""Tests — chargement des artefacts depuis le volume Railway (ordre 1501).

Migration deploy volume : l'app lit formations.json + index depuis le volume monté
(RAILWAY_VOLUME_MOUNT_PATH, /app/data en prod), fail-fast si absent.
"""
from pathlib import Path

import pytest


def test_resolve_paths_default_relatif(monkeypatch):
    # Approche A : défauts relatifs. data/embeddings/... = /app/data/embeddings = volume
    # (cwd=/app) ; data/processed/... = image. Pas de dérivation RAILWAY_VOLUME_MOUNT_PATH.
    for k in ("ORIENTIA_FICHES_PATH", "ORIENTIA_INDEX_PATH", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(k, raising=False)
    from src.api.server import _resolve_artifact_paths
    fiches, index = _resolve_artifact_paths()
    assert fiches == Path("data/processed/formations.json")
    assert index == "data/embeddings/formations.index"


def test_railway_volume_mount_path_ignore(monkeypatch):
    # Le mount est /app/data/embeddings (pas /app/data) -> on N'utilise PAS
    # RAILWAY_VOLUME_MOUNT_PATH (le dériver donnerait /app/data/embeddings/embeddings).
    # Les chemins relatifs s'alignent déjà sur le volume.
    for k in ("ORIENTIA_FICHES_PATH", "ORIENTIA_INDEX_PATH"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", "/app/data/embeddings")
    from src.api.server import _resolve_artifact_paths
    fiches, index = _resolve_artifact_paths()
    assert fiches == Path("data/processed/formations.json")  # relatif, ignoré le mount path
    assert index == "data/embeddings/formations.index"


def test_resolve_paths_explicit_override_wins(monkeypatch):
    # ORIENTIA_* (prod les a, relatifs corrects) prime sur le défaut.
    monkeypatch.setenv("ORIENTIA_FICHES_PATH", "/custom/f.json")
    monkeypatch.delenv("ORIENTIA_INDEX_PATH", raising=False)
    from src.api.server import _resolve_artifact_paths
    fiches, index = _resolve_artifact_paths()
    assert fiches == Path("/custom/f.json")
    assert index == "data/embeddings/formations.index"


def test_require_artifacts_raises_if_absent(tmp_path):
    from src.api.server import _require_artifacts
    with pytest.raises(RuntimeError, match="Artefacts volume absents"):
        _require_artifacts(tmp_path / "nope.json", str(tmp_path / "nope.index"))


def test_require_artifacts_ok_if_present(tmp_path):
    from src.api.server import _require_artifacts
    f = tmp_path / "f.json"
    f.write_text("[]")
    i = tmp_path / "i.index"
    i.write_text("x")
    _require_artifacts(f, str(i))  # ne lève pas
