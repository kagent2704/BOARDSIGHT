from __future__ import annotations

import contextlib
import importlib
import io

_IMPORT_CACHE: dict[str, object | None] = {}


def optional_import(module_name: str):
    if module_name in _IMPORT_CACHE:
        return _IMPORT_CACHE[module_name]

    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            module = importlib.import_module(module_name)
        _IMPORT_CACHE[module_name] = module
        return module
    except Exception:
        _IMPORT_CACHE[module_name] = None
        return None


def dependency_available(module_name: str) -> bool:
    return optional_import(module_name) is not None
