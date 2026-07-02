"""
Test that PermissionLevel has a single source of truth.
This prevents the duplication issue where PermissionLevel was defined in both
core/permissions.py and core/interaction_registry.py.
"""
import ast
import sys
from pathlib import Path


def find_permission_level_definitions():
    """Find all definitions of PermissionLevel class or enum."""
    definitions = []
    
    for py_file in Path(".").rglob("*.py"):
        if "__pycache__" in str(py_file) or ".venv" in str(py_file):
            continue
            
        try:
            with open(py_file) as f:
                tree = ast.parse(f.read(), filename=str(py_file))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "PermissionLevel":
                    definitions.append(str(py_file))
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "PermissionLevel":
                            definitions.append(str(py_file))
        except (SyntaxError, ValueError):
            pass
    
    return definitions


def test_permission_level_single_source():
    """Test that PermissionLevel is only defined once (not duplicated)."""
    definitions = find_permission_level_definitions()
    
    # Filter out test file itself
    definitions = [d for d in definitions if "test_permission_level_single_source" not in d]
    
    # Check for class definitions only (imports don't count)
    class_definitions = []
    for py_file in Path(".").rglob("*.py"):
        if "__pycache__" in str(py_file) or ".venv" in str(py_file) or "test_permission_level_single_source" in str(py_file):
            continue
        try:
            with open(py_file) as f:
                content = f.read()
            if "class PermissionLevel" in content:
                class_definitions.append(str(py_file))
        except:
            pass
    
    if len(class_definitions) > 1:
        print(f"ERROR: PermissionLevel class defined in {len(class_definitions)} locations:")
        for d in class_definitions:
            print(f"  - {d}")
        assert False, f"PermissionLevel must have a single source of truth. Found class definitions in: {class_definitions}"
    
    print(f"✅ PermissionLevel has single source of truth (class defined in: {class_definitions})")


def test_permission_level_importable_from_core():
    """Test that PermissionLevel can be imported from core.permissions."""
    from core.permissions import PermissionLevel
    assert hasattr(PermissionLevel, "OWNER")
    assert hasattr(PermissionLevel, "GLOBAL_ADMIN")
    assert hasattr(PermissionLevel, "SERVER_ADMIN")
    assert hasattr(PermissionLevel, "ALLIANCE_ADMIN")
    assert hasattr(PermissionLevel, "MEMBER")
    print("✅ PermissionLevel importable from core.permissions")


def test_registry_uses_core_permission_level():
    """Test that interaction_registry imports PermissionLevel from core.permissions."""
    import ast
    
    registry_path = Path("core/interaction_registry.py")
    with open(registry_path) as f:
        content = f.read()
    
    # Check that it imports PermissionLevel
    assert "from core.permissions import PermissionLevel" in content, \
        "interaction_registry.py must import PermissionLevel from core.permissions"
    
    # Check that it does NOT define its own PermissionLevel
    assert "class PermissionLevel" not in content or \
           "from core.permissions import PermissionLevel" in content.split("class PermissionLevel")[0], \
        "interaction_registry.py must not define its own PermissionLevel class"
    
    print("✅ interaction_registry uses PermissionLevel from core.permissions")


if __name__ == "__main__":
    print("Running PermissionLevel single source tests...\n")
    test_permission_level_single_source()
    test_permission_level_importable_from_core()
    test_registry_uses_core_permission_level()
    print("\n✅ All tests passed!")
