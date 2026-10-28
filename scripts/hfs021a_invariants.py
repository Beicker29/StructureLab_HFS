"""Narrow source invariants for the package migration; no numerical tolerance."""
import ast


def assert_import_migration_only(before: str, after: str) -> None:
    """Only the approved package prefix may change, including -m/dynamic imports.

Do not strip imports, constants, branches or assertions: compare the complete
tree against one explicit spelling transformation of the approved source.
"""
    expected = ast.parse(before.replace("src.steel_design", "steel_design"))
    actual = ast.parse(after)
    assert ast.dump(expected, include_attributes=False) == ast.dump(actual, include_attributes=False), (
        "Change beyond the approved import/module-prefix migration")


def assert_trace_identifier_compatibility_only(before: str, after: str) -> None:
    """Allow only the historical JSON ID spelling adapter, never coverage logic."""
    anchor = "    claims = _CLAIMS.get(implementation, ())\n"
    assert before.count(anchor) == 1
    expected = before.replace(anchor, anchor +
        '    module = implementation.__module__\n'
        '    identifier_module = "src." + module if module.startswith("steel_design.") else module\n')
    expected = expected.replace('implementation=f"{implementation.__module__}.{implementation.__qualname__}"',
                                'implementation=f"{identifier_module}.{implementation.__qualname__}"')
    assert ast.dump(ast.parse(expected), include_attributes=False) == ast.dump(ast.parse(after), include_attributes=False), (
        "Change beyond historical trace identifier compatibility")
