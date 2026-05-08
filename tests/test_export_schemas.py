"""Tests for `scripts/export_schemas.py`.

Two responsibilities:
  1. Verify the script can discover and render JSON Schemas for every Pydantic
     model in `orchestrator.schemas`.
  2. Catch the case where someone modifies `orchestrator/schemas.py` without
     regenerating `schemas/*.schema.json` (`--check` mode).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_schemas.py"


def _load_export_module():
    spec = importlib.util.spec_from_file_location("speca_export_schemas", EXPORT_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def export_module():
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        yield _load_export_module()
    finally:
        sys.path.remove(str(REPO_ROOT / "scripts"))


def test_collects_at_least_one_model(export_module):
    models = export_module.collect_models(export_module.SOURCE_MODULE)
    assert len(models) > 0, "expected at least one BaseModel subclass"
    names = [m.__name__ for m in models]
    # A few key boundary schemas the CLI wizard will validate.
    for required in ("TargetInfo", "BugBountyScopeInfo", "Phase01aState"):
        assert required in names, f"{required} should be in exported models"


def test_render_schema_produces_dict(export_module):
    models = export_module.collect_models(export_module.SOURCE_MODULE)
    schema = export_module.render_schema(models[0])
    assert isinstance(schema, dict)
    # Pydantic-generated schemas always carry these keys
    assert "properties" in schema or "$defs" in schema or "type" in schema


def test_serialize_is_stable(export_module):
    models = export_module.collect_models(export_module.SOURCE_MODULE)
    schema = export_module.render_schema(models[0])
    a = export_module.serialize_schema(schema)
    b = export_module.serialize_schema(schema)
    assert a == b
    assert a.endswith("\n")
    # Parses back as JSON
    json.loads(a)


def test_write_then_check_in_sync(tmp_path, export_module):
    models = export_module.collect_models(export_module.SOURCE_MODULE)
    out = tmp_path / "out"
    for m in models:
        export_module.write_schema(m, out)
    diffs = export_module.check_in_sync(models, out)
    assert diffs == [], f"freshly-written schemas should be in sync: {diffs}"


def test_check_detects_stale(tmp_path, export_module):
    models = export_module.collect_models(export_module.SOURCE_MODULE)
    out = tmp_path / "out"
    for m in models:
        export_module.write_schema(m, out)

    # Mutate one file
    target = out / f"{models[0].__name__}.schema.json"
    target.write_text("{}\n", encoding="utf-8")

    diffs = export_module.check_in_sync(models, out)
    assert any("stale:" in d and target.name in d for d in diffs), diffs


def test_check_detects_orphan(tmp_path, export_module):
    models = export_module.collect_models(export_module.SOURCE_MODULE)
    out = tmp_path / "out"
    for m in models:
        export_module.write_schema(m, out)
    (out / "Bogus.schema.json").write_text("{}\n", encoding="utf-8")

    diffs = export_module.check_in_sync(models, out)
    assert any("orphan:" in d for d in diffs), diffs


def test_committed_schemas_in_sync_with_source(export_module):
    """If this fails, run `python scripts/export_schemas.py` and commit the diff.

    Guards against `orchestrator/schemas.py` being edited without the
    corresponding regeneration of `schemas/*.schema.json` — the JSON Schemas
    are the language-neutral data contract consumed by `speca-cli`.
    """
    if not SCHEMAS_DIR.exists():
        pytest.skip("schemas/ directory not present in this checkout")

    models = export_module.collect_models(export_module.SOURCE_MODULE)
    diffs = export_module.check_in_sync(models, SCHEMAS_DIR)
    assert diffs == [], (
        "schemas/ is out of sync with orchestrator/schemas.py. "
        "Re-run `python scripts/export_schemas.py` and commit the result.\n"
        + "\n".join(f"  {d}" for d in diffs)
    )


def test_target_info_schema_rejects_empty_core_strings():
    schema = json.loads((SCHEMAS_DIR / "TargetInfo.schema.json").read_text(encoding="utf-8"))

    for field in ("target_repo", "target_commit", "local_checkout"):
        prop = schema["properties"][field]
        assert prop["minLength"] == 1
        assert prop["pattern"] == "\\S"
