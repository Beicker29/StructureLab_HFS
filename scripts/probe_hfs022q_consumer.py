"""Standalone external consumer: public APIs and hand-authored JSON only.

Run with an installed interpreter (-I -B), outside the source checkout.
No test-module imports, source-path injections or production fixture generators.
Application files are read by this consumer before the guarded API phase.
"""
import argparse
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", type=Path)
    parser.add_argument("--aliases", action="store_true")
    args = parser.parse_args()
    raw_bytes = args.fixtures.read_bytes()
    specimens = json.loads(raw_bytes)["cases"]
    sys_path_before = list(sys.path)
    forbidden = ("steel_design.engine", "steel_design.execution", "steel_design.run",
                 "steel_design.reporting", "steel_design.sections.repository",
                 "steel_design.sections.loader", "steel_design.sections.geometry",
                 "steel_design.domain.routing", "steel_design.domain.rules",
                 "steel_design.domain.evaluators", "steel_design.domain.coverage")
    guarded = True

    class ImportGuard:
        def find_spec(self, fullname, path=None, target=None):
            if guarded and any(fullname == name or fullname.startswith(name + ".") for name in forbidden):
                raise AssertionError("Forbidden dependency: " + fullname)

    sys.meta_path.insert(0, ImportGuard())

    def audit(event, values):
        if not guarded:
            return
        if event in ("socket.connect", "subprocess.Popen", "os.mkdir", "os.remove", "os.rename"):
            raise AssertionError("API side effect: " + event)
        if event == "open":
            path, mode, flags = values
            if ((isinstance(mode, str) and any(c in mode for c in "wax+"))
                    or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
                raise AssertionError("API wrote a file")
            if str(path).lower().endswith((".json", ".xlsx", ".pdf", ".svg")):
                raise AssertionError("API read an application file")

    def profile(frame, event, arg):
        if (guarded and event == "call" and frame.f_code.co_name != "<module>"
                and frame.f_globals.get("__name__", "").startswith("steel_design.codes")):
            raise AssertionError("Engineering calculation during contract use")

    sys.addaudithook(audit)
    sys.setprofile(profile)
    from steel_design.contracts import ContractError, dump_json, load_json, validate_document

    results = []
    for fixture in specimens:
        text = fixture.get("json_text") or json.dumps(fixture["document"], ensure_ascii=False)
        original = json.loads(text)
        untouched = copy.deepcopy(original)
        record = {"id": fixture["id"]}
        try:
            document = load_json(text)
        except ContractError as error:
            assert not fixture["python"], fixture["id"]
            assert (error.code, error.path) == (fixture["code"], fixture["path"]), fixture["id"]
            assert bool(error.__cause__) == fixture["cause"], fixture["id"]
            # The dictionary API cannot recover duplicate text keys already lost.
            if "json_text" not in fixture:
                try:
                    validate_document(original)
                except ContractError as second:
                    assert (second.code, second.path) == (error.code, error.path)
                else:
                    raise AssertionError("Dictionary API accepted invalid specimen")
            record.update(accepted=False, code=error.code, path=error.path,
                          cause=type(error.__cause__).__name__ if error.__cause__ else None)
        else:
            assert fixture["python"], fixture["id"]
            encoded = dump_json(document)
            assert json.loads(encoded) == original, fixture["id"]
            assert dump_json(load_json(encoded)) == encoded
            assert dump_json(validate_document(original)) == encoded
            assert dump_json(document) == encoded  # deterministic, no payload repair
            record.update(accepted=True, roundtrip=True, serialized_sha256=hashlib.sha256(encoded.encode()).hexdigest())
        assert original == untouched, fixture["id"]
        record["original_unmodified"] = True
        results.append(record)
    sys.setprofile(None)
    modules = sorted(name for name in sys.modules if name == "steel_design" or name.startswith("steel_design."))
    assert not any(name in sys.modules for name in forbidden)
    assert sys.path == sys_path_before
    answer = {"contract_modules": modules, "module_files": {name: sys.modules[name].__file__ for name in modules},
              "sys_path": sys.path, "fixture_sha256": hashlib.sha256(raw_bytes).hexdigest(),
              "guarded_contract_phase": True, "fixtures": results}

    if args.aliases:
        # Explicit second phase: execution legitimately imports its engine.
        # The contract-only phase above must succeed first.
        guarded = False
        from steel_design.execution import (OutputOptions, extract_output_options,
            merge_case_payload, prepare_cases, validate_bundle_shape)
        full = next(f["document"] for f in specimens if f["id"] == "input_complete")
        assert type(validate_document(full).output) is OutputOptions
        symbols = (OutputOptions, extract_output_options, merge_case_payload, prepare_cases, validate_bundle_shape)
        # Inspect the already-loaded defining module, never import a private API.
        for symbol in symbols:
            owner = inspect.getmodule(symbol)
            assert owner.__name__ == "steel_design.preparation"
            assert getattr(owner, symbol.__name__) is symbol
        bundle = next(f for f in specimens if f["id"] == "bundle_partial")
        original = copy.deepcopy(bundle["document"]["payload"])
        actual = [{"Pu": case.loads.Pu, "Fy": case.material.Fy, "Fu": case.material.Fu,
                   "Kx": case.factors.Kx, "tag": tag, "write_results_json": options["write_results_json"]}
                  for case, payload, options, tag in prepare_cases(original)]
        assert actual == bundle["expected_prepared"]
        assert original == bundle["document"]["payload"]
        answer["public_aliases"] = {symbol.__name__: {"owner": symbol.__module__, "signature": str(inspect.signature(symbol))} for symbol in symbols}
        answer["prepared_bundle"] = actual
    print(json.dumps(answer, indent=2))


if __name__ == "__main__":
    main()
