"""
Test: No visible placeholders in callbacks
Ensures no TODO or "under development" messages in user-facing callbacks.
© MANSOUR — WOS-M. All rights reserved.
"""
import pytest
import re
from pathlib import Path


FORBIDDEN_PATTERNS = [
    "TODO",
    "قيد التطوير",
    "غير مفعّلة",
    "Coming soon",
    "Not implemented",
    "Placeholder",
    "WIP",
    "under development",
    "⚠️ هذه الميزة قيد التطوير",
]


def get_all_callbacks_from_modules():
    """Extract all callback implementations from module views."""
    callbacks = []
    
    for views_file in Path("modules").rglob("views.py"):
        with open(views_file) as f:
            content = f.read()
        
        # Find all async def callback functions
        pattern = r'async def (\w+_callback)\([^)]*\):'
        matches = re.findall(pattern, content)
        
        for match in matches:
            # Extract the full function body
            func_pattern = rf'async def {match}\([^)]*\):(.*?)(?=\nasync def |\nclass |\Z)'
            func_match = re.search(func_pattern, content, re.DOTALL)
            
            if func_match:
                func_body = func_match.group(1)
                callbacks.append({
                    "name": match,
                    "file": str(views_file),
                    "body": func_body
                })
    
    return callbacks


class TestNoVisiblePlaceholders:
    """Test that no callbacks have visible placeholder messages."""
    
    def test_no_todo_in_callbacks(self):
        """No callback should contain TODO comments in the function body."""
        callbacks = get_all_callbacks_from_modules()
        
        violations = []
        for callback in callbacks:
            if "TODO" in callback["body"]:
                # Check if it's in a comment or actual work needed
                lines = callback["body"].split("\n")
                for i, line in enumerate(lines):
                    if "# TODO:" in line:
                        violations.append(f"{callback['name']} in {callback['file']}")
        
        assert len(violations) == 0, (
            f"Found {len(violations)} callbacks with TODO:\n" +
            "\n".join(f"  ❌ {v}" for v in violations)
        )
    
    def test_no_placeholder_messages(self):
        """No callback should send 'under development' or similar messages to users."""
        callbacks = get_all_callbacks_from_modules()
        
        violations = []
        for callback in callbacks:
            body = callback["body"]
            for pattern in FORBIDDEN_PATTERNS:
                if pattern in body:
                    violations.append(f"{callback['name']} in {callback['file']}: '{pattern}'")
                    break
        
        assert len(violations) == 0, (
            f"Found {len(violations)} callbacks with placeholder messages:\n" +
            "\n".join(f"  ❌ {v}" for v in violations)
        )
    
    def test_no_incomplete_callbacks(self):
        """Callbacks should not just defer or send generic 'under development'."""
        callbacks = get_all_callbacks_from_modules()
        
        incomplete = []
        for callback in callbacks:
            body = callback["body"].strip()
            
            # Check for trivial callbacks that just send placeholder
            if (
                body.count('\n') < 3 and  # Very short
                any(p in body for p in ["⚠️", "قيد", "Coming", "Not implemented", "Placeholder"])
            ):
                incomplete.append(callback["name"])
        
        assert len(incomplete) == 0, (
            f"Found {len(incomplete)} incomplete callbacks:\n" +
            "\n".join(f"  ❌ {c}" for c in incomplete)
        )


def test_summary():
    """Print summary of placeholder check."""
    callbacks = get_all_callbacks_from_modules()
    print(f"\n{'='*60}")
    print("PLACEHOLDER CHECK SUMMARY")
    print(f"{'='*60}")
    print(f"Total callbacks checked: {len(callbacks)}")
    
    # Check for issues
    issues = 0
    for callback in callbacks:
        body = callback["body"]
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in body:
                issues += 1
                break
    
    print(f"Callbacks with placeholders: {issues}")
    print(f"Status: {'✅ CLEAN' if issues == 0 else '❌ FOUND ISSUES'}")
    print(f"{'='*60}")
    
    assert issues == 0, f"Found {issues} callbacks with placeholders"