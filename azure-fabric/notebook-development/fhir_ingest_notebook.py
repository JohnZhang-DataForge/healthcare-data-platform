"""Offline-only compatibility import for the single Fabric Native Notebook implementation."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys

_NOTEBOOK = Path(__file__).resolve().parents[1] / "workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py"
_SPEC = importlib.util.spec_from_file_location("healthcare_p2_native_notebook", _NOTEBOOK)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("NATIVE_FABRIC_NOTEBOOK_IMPORT_FAILED")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
for _name, _value in vars(_MODULE).items():
    if not (_name.startswith("__") and _name.endswith("__")):
        globals()[_name] = _value
