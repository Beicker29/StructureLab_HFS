"""Generate or read-only verify canonical contract schemas with pinned dev dependencies."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

from steel_design.contracts import CONTRACT_KINDS, CONTRACT_VERSION, get_schema


def schema_files() -> dict[str, bytes]:
    """One generator shared by command and regression; UTF-8/LF, sorted keys."""
    files = {}
    for kind in CONTRACT_KINDS:
        for mode in ("validation", "serialization"):
            files[f"{kind}.{mode}.json"] = (
                json.dumps(get_schema(kind, mode=mode), ensure_ascii=False, sort_keys=True, indent=2)
                + "\n").encode("utf-8")
    manifest = {"contract_version": CONTRACT_VERSION,
                "generator": "steel_design.contracts.get_schema",
                "dependencies": {name: importlib.metadata.version(name) for name in ("pydantic", "pydantic_core")},
                "sha256": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    files["manifest.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parents[1] / "docs/schemas/contracts/1.0")
    parser.add_argument("--check", action="store_true", help="Read only; exit 1 on drift, missing or unexpected files")
    args = parser.parse_args()
    expected = schema_files()
    if args.check:
        actual = {p.name: p.read_bytes() for p in args.directory.glob("*.json")}
        differences = sorted(name for name in actual.keys() | expected.keys() if actual.get(name) != expected.get(name))
        print(json.dumps({"mode": "check", "differences": differences, "files": len(expected)}))
        return int(bool(differences))
    args.directory.mkdir(parents=True, exist_ok=True)
    for name, data in expected.items():
        (args.directory / name).write_bytes(data)
    print(json.dumps({"mode": "generate", "files": len(expected)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
