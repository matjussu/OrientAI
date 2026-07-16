"""Gate CI : versions de modèles pinnées + fingerprint de provenance (H1 lot 1.5).

L'audit 15/07 relevait des alias -latest partout (drift silencieux possible,
embeddings compris) et l'impossibilité de savoir quelle version de prompt /
corpus / index a produit une réponse. Ces tests verrouillent les deux fixes.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.rag.models import MISTRAL_EMBED, MISTRAL_LARGE, MISTRAL_MEDIUM, MISTRAL_SMALL

ROOT = Path(__file__).resolve().parents[1]

# Zones où AUCUN alias -latest ne doit exister (chemin servi + bench + Phase 3).
# Exception temporaire : fact_checker.py, déplacé vers experimental/ par la
# branche lot 1.4 — à pinner dans un suivi post-merge (1 ligne).
_SCANNED = ("src",)
_LATEST = re.compile(r'"mistral-[a-z0-9-]*-latest"|"[a-z]*-latest"')
_EXCEPTIONS = {"fact_checker.py"}


def test_aucun_alias_latest_dans_src():
    offenders: list[str] = []
    for zone in _SCANNED:
        for py in (ROOT / zone).rglob("*.py"):
            if py.name in _EXCEPTIONS or py.name == "models.py":
                continue
            if _LATEST.search(py.read_text(encoding="utf-8")):
                offenders.append(str(py.relative_to(ROOT)))
    assert offenders == [], (
        f"alias -latest réintroduits (pinner via src/rag/models.py) : {offenders}"
    )


def test_pins_sont_des_versions_datees():
    for pin in (MISTRAL_MEDIUM, MISTRAL_SMALL, MISTRAL_LARGE, MISTRAL_EMBED):
        assert "latest" not in pin
        assert re.search(r"\d{4}$|\d{4}\b", pin), f"pin non daté : {pin}"


def test_embed_model_est_celui_de_l_index():
    """mistral-embed-2312 est la SEULE version datée de mistral-embed ayant
    jamais existé : l'index FAISS a nécessairement été construit avec. Si ce
    test casse parce que quelqu'un a bumpé MISTRAL_EMBED : il faut un re-embed
    complet du corpus + gate golden retrieval AVANT (cf src/rag/models.py)."""
    assert MISTRAL_EMBED == "mistral-embed-2312"


def test_embeddings_module_utilise_le_pin():
    from src.rag.embeddings import EMBED_MODEL
    assert EMBED_MODEL == MISTRAL_EMBED


class TestProvenance:
    def test_fingerprint_forme_et_stabilite(self, tmp_path):
        from src.api.provenance import build_fingerprint

        f = tmp_path / "corpus.json"
        f.write_text('[{"nom": "test"}]')
        idx = tmp_path / "index.bin"
        idx.write_bytes(b"fake-index")

        fp1 = build_fingerprint(f, idx)
        fp2 = build_fingerprint(f, idx)
        assert fp1 == fp2, "le fingerprint doit être déterministe"
        assert set(fp1) == {"prompt", "corpus", "index", "model_gen", "model_aux", "model_embed"}
        assert len(fp1["prompt"]) == 12 and len(fp1["corpus"]) == 12
        assert fp1["model_gen"] == MISTRAL_MEDIUM

    def test_fingerprint_change_si_le_corpus_change(self, tmp_path):
        from src.api.provenance import build_fingerprint

        f = tmp_path / "corpus.json"
        idx = tmp_path / "index.bin"
        idx.write_bytes(b"fake-index")
        f.write_text("[1]")
        h1 = build_fingerprint(f, idx)["corpus"]
        f.write_text("[2]")
        h2 = build_fingerprint(f, idx)["corpus"]
        assert h1 != h2

    def test_artefact_absent_ne_crashe_pas(self, tmp_path):
        from src.api.provenance import build_fingerprint

        fp = build_fingerprint(tmp_path / "inexistant.json", tmp_path / "inexistant.bin")
        assert fp["corpus"] == "absent" and fp["index"] == "absent"
        assert len(fp["prompt"]) == 12  # le hash prompt ne dépend pas des fichiers

    def test_prompt_hash_change_si_une_regle_change(self, monkeypatch):
        """Le hash prompt suit le prompt SERVI : si une règle disparaît ou
        change, le fingerprint doit changer (c'est sa raison d'être)."""
        import src.api.provenance as prov
        import src.prompt.system_v4_strict as v4

        h_avant = prov._prompt_hash()
        monkeypatch.setattr(
            v4, "SYSTEM_PROMPT_V4_STRICT",
            v4.SYSTEM_PROMPT_V4_STRICT.replace("MAX 250 mots", "MAX 999 mots"),
        )
        h_apres = prov._prompt_hash()
        assert h_avant != h_apres
