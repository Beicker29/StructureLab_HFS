"""Offline documentary evidence; never evaluates a structural case.

Run --pdf with an environment containing pypdf, or --registry with the
installed project. Outputs are snapshots, not a second normative registry.
"""
import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[3]
PDF_SHA = "25c4bf59b4c6fd00589e32a6ddac92cc9fd6be30dd5da07fc7c5f7fd475b2361"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pdf_evidence():
    from pypdf import PdfReader

    path = ROOT / "a360-22w.pdf"
    sha = digest(path.read_bytes())
    if sha != PDF_SHA:
        raise SystemExit("Local PDF differs from the reviewed source")
    reader = PdfReader(path)
    # Documentary anchors selected by reading the PDF, not from the router.
    anchors = {
        "A1": [69], "A3": list(range(74, 80)),
        "B4.1/Table B4.1b": [87, 88, 90, 91],
        "D2/D3": list(range(100, 104)), "E3/E4": list(range(108, 112)),
        "E5": [111, 112, 113], "E6": [113, 114, 115, 116], "E7": [116, 117],
        "F1": [119, 120], "F2": [121, 122, 123], "F3": [123, 124],
        "F4/UN": [124, 125, 126, 127], "F5/F6": [127, 128, 129, 130],
        "F7": [130, 131, 132, 133], "G4/G5": [148, 149],
        "H1": [150, 151, 152], "H3": [153, 154, 155],
        "I3": [171, 172, 173, 174], "I5": [176, 177, 178],
        "Commentary front": [355], "C-I5": [518, 519, 520, 521, 522],
        "Errata 2025 targets": [128, 132, 204, 221, 235, 236, 253, 309, 310, 349, 515, 545, 683, 692],
        "Errata 2026 targets": [58, 151, 177, 188, 270, 671, 698],
    }
    pages = sorted({1, 3} | {p for values in anchors.values() for p in values})
    supplements = {}
    for filename, expected in (
        ("errata_360-22_01232025.pdf", "b2c8a9db622f583ebff013be1d1b4ffd3b992f7c7344d6cb815991ed400a1be6"),
        ("errata_360-22_09232026.pdf", "d53ff5cc753cfcf6af70fd10355895b0120074527946f997084482fb626732e6"),
        ("a341-22w.pdf", "34cdd4a45360b5e3cb39f9fbb55640af79ece0deb9070a112aaccb938c027e0c"),
    ):
        local = ROOT / filename
        actual = digest(local.read_bytes())
        if actual != expected:
            raise SystemExit(f"Source changed: {filename}")
        other = PdfReader(local)
        supplements[filename] = {
            "sha256": actual, "bytes": local.stat().st_size, "pages": len(other.pages),
            "metadata": dict(other.metadata),
            "provenance": "User supplied local errata" if filename.startswith("errata") else "Repository; separate seismic scope",
            "page_text_sha256_utf8": {
                str(i+1): digest(page.extract_text().encode("utf-8"))
                for i, page in enumerate(other.pages)
            } if filename.startswith("errata") else {},
        }
    return {
        "scope": "LOCAL_PDFS_ONLY; includes user supplied 2025 and 2026 errata; no remote byte authentication",
        "python": platform.python_version(), "pypdf": importlib.metadata.version("pypdf"),
        "path": path.name, "sha256": sha, "bytes": path.stat().st_size,
        "pages": len(reader.pages), "metadata": dict(reader.metadata),
        "supplements": supplements,
        "anchors_pdf_1_based": anchors,
        "page_text_sha256_utf8": {
            str(p): digest(reader.pages[p-1].extract_text().encode("utf-8")) for p in pages
        },
        "warning": "Text hashes prove extraction identity, not equation accuracy; visual review required.",
    }


def registry_evidence():
    from steel_design.domain.routing.profile_router import RULE_DEFINITIONS

    archive = ROOT / "docs/audit/hfs024/evidence/after.zip"
    with zipfile.ZipFile(archive) as bundle:
        trace_bytes = bundle.read("traces-wheel.json")
    traces = json.loads(trace_bytes)
    rows = {}
    for key, definition in RULE_DEFINITIONS.items():
        metadata = definition.metadata.model_dump(mode="json")
        observations = []
        for example, data in traces["examples"].items():
            for evaluation in data["trace"]["evaluations"]:
                if evaluation["rule_id"] == key:
                    observations.append({
                        "example": example, "evaluation_index": evaluation["evaluation_index"],
                        "outcome": evaluation["outcome"],
                        "step_producers": sorted({s["producer"] for s in evaluation["steps"]}),
                    })
        cls = definition.rule_class
        rows[key] = {
            "implementation": f"{cls.__module__}:{cls.__qualname__}" if cls else None,
            **{field: metadata[field] for field in (
                "citations", "calculation_refs", "software_tests", "independent_tests",
                "independent_scope", "implementation_state", "normative_validation", "findings")},
            "historical_trace_observations": observations,
            "review_status": "Inventory link only; consult impact-matrix.md for actual local review",
        }
    return {
        "python": platform.python_version(),
        "source": "RULE_DEFINITIONS; read-only snapshot, not executable applicability",
        "trace_archive": archive.relative_to(ROOT).as_posix(),
        "trace_archive_sha256": digest(archive.read_bytes()),
        "trace_member": "traces-wheel.json", "trace_member_sha256": digest(trace_bytes),
        "entries": len(rows), "rules": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pdf", action="store_true")
    mode.add_argument("--registry", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("Choose a new evidence path; historical captures are immutable")
    result = pdf_evidence() if args.pdf else registry_evidence()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {args.out}; no calculations or normative accreditation")


if __name__ == "__main__":
    main()
