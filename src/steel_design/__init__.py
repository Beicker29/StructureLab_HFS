"""StructureLab HFS; public imports are documented per module, without eager I/O.

The former src.steel_design namespace is intentionally unsupported. Reject it
before any model can be initialized under a second Python identity, including
when the checkout root makes the implicit src namespace discoverable.
"""

if __name__ != "steel_design":
    raise ImportError(
        "The src.steel_design namespace has been retired. "
        "Install structurelab-hfs (pip install -e . for development) and import "
        "steel_design; use python -m steel_design.run."
    )
