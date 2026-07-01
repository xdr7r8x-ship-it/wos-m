"""
Tests for No Production Placeholder Text
Verifies no placeholder text exists in production code.
© MANSOUR — WOS-M. All rights reserved.
"""
import os
import re
import pytest


FORBIDDEN_PATTERNS = [
    r"قيد التطوير",
    r"غير مفعّلة",
    r"Coming soon",
    r"Not implemented",
    r"Placeholder",
    r"TODO",
    r"coming soon",
    r"disabled feature",
    r"under development",
    r"not yet implemented",
    r"work in progress",
    r"WIP",
    r"not ready",
]


class TestNoProductionPlaceholderText:
    """Tests to ensure no placeholder text in production code."""

    def test_no_placeholder_in_bot(self):
        """No placeholder text in core/bot.py."""
        bot_path = os.path.join(os.path.dirname(__file__), "..", "core", "bot.py")
        if os.path.exists(bot_path):
            with open(bot_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            for pattern in FORBIDDEN_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                assert len(matches) == 0, \
                    f"Found forbidden pattern '{pattern}' in bot.py: {matches}"

    def test_no_placeholder_in_views(self):
        """No placeholder text in views (except legitimate Discord UI placeholder param)."""
        views_dir = os.path.join(os.path.dirname(__file__), "..", "views")
        if os.path.exists(views_dir):
            for filename in os.listdir(views_dir):
                if filename.endswith(".py"):
                    filepath = os.path.join(views_dir, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    for pattern in FORBIDDEN_PATTERNS:
                        if pattern.lower() == "placeholder":
                            # Skip legitimate Discord.py placeholder parameter
                            continue
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        assert len(matches) == 0, \
                            f"Found '{pattern}' in views/{filename}: {matches}"

    def test_no_placeholder_in_modules(self):
        """No placeholder text in modules (except legitimate Discord UI placeholder param)."""
        modules_dir = os.path.join(os.path.dirname(__file__), "..", "modules")
        if os.path.exists(modules_dir):
            for module_name in os.listdir(modules_dir):
                module_path = os.path.join(modules_dir, module_name)
                if os.path.isdir(module_path):
                    for filename in os.listdir(module_path):
                        if filename.endswith(".py"):
                            filepath = os.path.join(module_path, filename)
                            with open(filepath, "r", encoding="utf-8") as f:
                                content = f.read()
                            
                            for pattern in FORBIDDEN_PATTERNS:
                                if pattern.lower() == "placeholder":
                                    # Skip legitimate Discord.py placeholder parameter
                                    continue
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                assert len(matches) == 0, \
                                    f"Found '{pattern}' in modules/{module_name}/{filename}"

    def test_no_placeholder_in_core(self):
        """No placeholder text in core modules."""
        core_dir = os.path.join(os.path.dirname(__file__), "..", "core")
        if os.path.exists(core_dir):
            for filename in os.listdir(core_dir):
                if filename.endswith(".py"):
                    filepath = os.path.join(core_dir, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    for pattern in FORBIDDEN_PATTERNS:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        assert len(matches) == 0, \
                            f"Found '{pattern}' in core/{filename}"
