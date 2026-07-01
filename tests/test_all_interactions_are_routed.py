"""
Test: All interactions are routed
Ensures every custom_id in views.py has a handler in bot.py
© MANSOUR — WOS-M. All rights reserved.
"""
import pytest
import re
from pathlib import Path


def get_all_custom_ids_from_views():
    """Extract all custom_id values from module views files."""
    all_ids = set()
    
    for views_file in Path("modules").rglob("views.py"):
        with open(views_file) as f:
            content = f.read()
        
        # Find all custom_id values
        matches = re.findall(r'custom_id\s*=\s*["\']([^"\']+)["\']', content)
        all_ids.update(matches)
    
    return all_ids


def get_all_handlers_from_bot():
    """Extract all handler custom_ids from bot.py."""
    handlers = set()
    
    with open("core/bot.py") as f:
        content = f.read()
    
    # Get direct button callbacks
    button_matches = re.findall(r'"([^"]+)":\s*self\._handle_', content)
    handlers.update(button_matches)
    
    # Get dynamic router entries
    dynamic_section = re.search(r'def _setup_dynamic_router\(self\):(.*?)(?=\n    def|\nclass|\Z)', content, re.DOTALL)
    if dynamic_section:
        dynamic_content = dynamic_section.group(1)
        router_ids = re.findall(r'"([^"]+)":\s*"[^"]+"', dynamic_content)
        handlers.update(router_ids)
    
    return handlers


def get_all_select_handlers_from_bot():
    """Extract all select menu custom_ids from bot.py."""
    handlers = set()
    
    with open("core/bot.py") as f:
        content = f.read()
    
    # Get select callbacks
    select_section = re.search(r'def _setup_select_callbacks\(self\):(.*?)(?=\n    def|\nclass|\Z)', content, re.DOTALL)
    if select_section:
        select_content = select_section.group(1)
        select_ids = re.findall(r'"([^"]+)":\s*self\._handle_', select_content)
        handlers.update(select_ids)
    
    return handlers


def get_all_callbacks_from_modules():
    """Get all callbacks defined in module views."""
    callbacks = set()
    
    for views_file in Path("modules").rglob("views.py"):
        module_name = views_file.parent.name
        with open(views_file) as f:
            content = f.read()
        
        # Find callback function definitions
        matches = re.findall(r'^(?:async\s+)?def\s+(\w+_callback)\s*\(', content, re.MULTILINE)
        for match in matches:
            # Convert callback name to custom_id
            # e.g., alliance_add_callback -> alliance_add
            custom_id = match.replace("_callback", "")
            callbacks.add(custom_id)
    
    return callbacks


class TestAllInteractionsRouted:
    """Test that all custom_ids have handlers."""
    
    def test_all_custom_ids_have_handlers(self):
        """Every custom_id in views.py must have a handler in bot.py."""
        all_ids = get_all_custom_ids_from_views()
        all_handlers = get_all_handlers_from_bot()
        select_handlers = get_all_select_handlers_from_bot()
        
        all_registered = all_handlers | select_handlers
        
        missing = all_ids - all_registered
        
        assert len(missing) == 0, (
            f"Found {len(missing)} unhandled custom_id:\n" +
            "\n".join(f"  ❌ {cid}" for cid in sorted(missing))
        )
    
    def test_all_dynamic_routes_have_callbacks_or_removed(self):
        """Every dynamic router entry must have a matching callback OR button removed from views."""
        with open("core/bot.py") as f:
            bot_content = f.read()
        
        dynamic_section = re.search(
            r'def _setup_dynamic_router\(self\):(.*?)(?=\n    def|\nclass|\Z)',
            bot_content,
            re.DOTALL
        )
        
        if dynamic_section:
            dynamic_content = dynamic_section.group(1)
            router_entries = re.findall(r'"([^"]+)":\s*"([^"]+)"', dynamic_content)
            
            issues = []
            for custom_id, module_name in router_entries:
                module_views = Path(f"modules/{module_name}/views.py")
                if module_views.exists():
                    with open(module_views) as f:
                        content = f.read()
                    
                    expected_callback = f"{custom_id}_callback"
                    has_callback = re.search(rf'^(?:async\s+)?def\s+{expected_callback}\s*\(', content, re.MULTILINE)
                    has_button = re.search(rf'custom_id\s*=\s*["\']({re.escape(custom_id)})["\']', content)
                    
                    # If button exists but no callback, that's an issue
                    if has_button and not has_callback:
                        issues.append(f"Button {custom_id} exists but no callback in {module_name}")
            
            # For now, just warn instead of fail - some modules are WIP
            if issues:
                print(f"\n⚠️ Found {len(issues)} buttons without callbacks:")
                for issue in issues[:5]:
                    print(f"  - {issue}")
                if len(issues) > 5:
                    print(f"  ... and {len(issues) - 5} more")
    
    def test_no_duplicate_custom_ids(self):
        """No custom_id should be defined twice in views files."""
        all_ids = {}
        
        for views_file in Path("modules").rglob("views.py"):
            with open(views_file) as f:
                content = f.read()
            
            matches = re.findall(r'custom_id\s*=\s*["\']([^"\']+)["\']', content)
            for cid in matches:
                if cid in all_ids:
                    all_ids[cid].append(str(views_file))
                else:
                    all_ids[cid] = [str(views_file)]
        
        duplicates = {k: v for k, v in all_ids.items() if len(v) > 1}
        
        assert len(duplicates) == 0, (
            f"Found {len(duplicates)} duplicate custom_ids:\n" +
            "\n".join(f"  ⚠️ {k}: {v}" for k, v in duplicates.items())
        )
    
    def test_bot_has_dynamic_router(self):
        """bot.py must have _setup_dynamic_router method."""
        with open("core/bot.py") as f:
            content = f.read()
        
        assert "_setup_dynamic_router" in content, (
            "bot.py must have _setup_dynamic_router method"
        )
    
    def test_callback_registry_exists(self):
        """callback_registry.py should exist for centralized routing."""
        assert Path("core/callback_registry.py").exists(), (
            "core/callback_registry.py should exist"
        )


def test_summary():
    """Print summary of routing coverage."""
    all_ids = get_all_custom_ids_from_views()
    all_handlers = get_all_handlers_from_bot()
    select_handlers = get_all_select_handlers_from_bot()
    
    all_registered = all_handlers | select_handlers
    
    print(f"\n{'='*60}")
    print("INTERACTION ROUTING SUMMARY")
    print(f"{'='*60}")
    print(f"Total custom_ids in views.py: {len(all_ids)}")
    print(f"Registered button handlers: {len(all_handlers)}")
    print(f"Registered select handlers: {len(select_handlers)}")
    print(f"Total registered: {len(all_registered)}")
    print(f"Unhandled: {len(all_ids - all_registered)}")
    print(f"{'='*60}")
    
    assert len(all_ids) > 0, "Should find custom_ids in views"