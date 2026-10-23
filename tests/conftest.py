"""Tests légers de ReaCue (aucun fichier audio lourd, aucun REAPER).

Le dossier des ressources REAPER est simulé dans un dossier temporaire AVANT tout import de
reacue_mcp (BRIDGE_DIR est calculé à l'import).
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "install"))

_RES = Path(tempfile.mkdtemp(prefix="reacue_res_"))
os.environ["REAPER_RESOURCE_PATH"] = str(_RES)
# jamais le vrai SongFormer pendant les tests (même s'il est installé à côté du dépôt)
os.environ["REACUE_STRUCTURE_ENGINE"] = "reacue"
# ni le vrai modèle de batterie (ADTOF)
os.environ["REACUE_DRUMS_ENGINE"] = "reacue"

import pytest  # noqa: E402


@pytest.fixture
def resdir():
    """Dossier des ressources REAPER simulé (partagé : BRIDGE_DIR pointe dessus)."""
    return _RES


@pytest.fixture
def bridge_dir(resdir):
    d = resdir / "ReaCueMCP"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def lang(bridge_dir):
    """Écrit reacue_settings.json avec la langue voulue ; rétablit le français ensuite."""
    import json
    from reacue_mcp import i18n
    p = bridge_dir / "reacue_settings.json"

    def set_(code, **extra):
        p.write_text(json.dumps({"language": code, **extra}), encoding="utf-8")
        i18n.set_lang(code)
        return code
    yield set_
    p.unlink(missing_ok=True)
    i18n.set_lang("fr")
