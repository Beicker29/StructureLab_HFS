"""Fresh-process identity probe, usable from checkout and external installations."""
import argparse
import builtins
import contextlib
import importlib
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch


PUBLIC = {
    "engine": ("SteelDesignEngine",),
    "models": ("SteelCase",),
    "sections.models": ("Section",),
    "sections.repository": ("SectionRepository",),
    "execution": ("execute_case", "iter_executions", "execute_payload", "execution_status"),
    "reporting": ("build_compact_summary", "build_detailed_results_payload"),
}


def probe(root, order):
    # Match python -c/-m cwd discovery without adding src or alternate packages.
    sys.path.insert(0, str(root))
    rejected = []
    def legacy():
        for name in ("src.steel_design", "src.steel_design.models", "src.steel_design.engine",
                     "src.steel_design.domain.errors", "src.steel_design.sections.models"):
            try:
                importlib.import_module(name)
            except ImportError as exc:
                rejected.append({"module": name, "type": type(exc).__name__, "message": str(exc)})
            else:
                raise AssertionError(f"Legacy identity loaded: {name}")
            assert not any(n.startswith("src.steel_design") for n in sys.modules)

    def forbidden(*args, **kwargs):
        raise AssertionError("Import attempted transport or filesystem side effects")

    # Import machinery/Pydantic legitimately read installed package metadata.
    # Reject writes and application data access without masking those reads.
    original_open, original_path_open = builtins.open, Path.open
    reads = []
    def check_read(path, mode):
        if any(flag in mode for flag in "wax+"):
            forbidden()
        if str(path).lower().endswith((".xlsx", ".json")):
            forbidden()
        reads.append(str(path))
    def read_only_open(path, mode="r", *args, **kwargs):
        check_read(path, mode)
        return original_open(path, mode, *args, **kwargs)
    def read_only_path_open(path, mode="r", *args, **kwargs):
        check_read(path, mode)
        return original_path_open(path, mode, *args, **kwargs)

    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr), \
            patch.object(builtins, "open", read_only_open), patch.object(Path, "open", read_only_path_open), \
            patch.object(Path, "mkdir", forbidden), patch.object(sys, "exit", forbidden):
        if order == "legacy-first":
            legacy()
        package = importlib.import_module("steel_design")
        # Minimal initializer must not eagerly load the engine or third parties.
        assert "steel_design.engine" not in sys.modules
        modules = {}
        items = list(PUBLIC.items())
        if order == "legacy-first":
            items.reverse()
        for module, symbols in items:
            loaded = importlib.import_module("steel_design." + module)
            for symbol in symbols:
                assert callable(getattr(loaded, symbol))
            modules[module] = loaded
        legacy()
        from steel_design.engine import SteelDesignEngine
        from steel_design.models import SteelCase
        from steel_design.domain.errors import ValidationError
        assert modules["engine"].SteelDesignEngine is SteelDesignEngine
        assert modules["models"].SteelCase is SteelCase
        assert ValidationError is importlib.import_module("steel_design.domain.errors").ValidationError
        assert not any(n.startswith("src.steel_design") for n in sys.modules)
    assert not stdout.getvalue() and not stderr.getvalue()
    assert "matplotlib" not in sys.modules
    return {"package": package.__name__, "origin": package.__file__, "order": order,
            "public_api": PUBLIC, "legacy_rejections": rejected, "side_effects": False,
            "class_module": SteelCase.__module__, "import_metadata_reads": reads}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--order", choices=("canonical-first", "legacy-first"), required=True)
    args = parser.parse_args()
    print(json.dumps(probe(args.root.resolve(), args.order), indent=2))
