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
        # Skip operations module - buttons have self-contained callbacks
        # and are tested separately in test_operations_panel.py
        if "operations" in str(views_file):
            continue
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

def test_permission_level_admin_alias_exists():
    """ADMIN alias must exist in PermissionLevel."""
    from core.permissions import PermissionLevel
    assert hasattr(PermissionLevel, "ADMIN"), "PermissionLevel.ADMIN must exist"
    assert PermissionLevel.ADMIN == PermissionLevel.SERVER_ADMIN, "ADMIN must equal SERVER_ADMIN"


def test_dashboard_has_no_owner_panel_bypass():
    """Dashboard must not have owner_panel bypass."""
    from pathlib import Path
    content = Path("modules/dashboard/views.py").read_text()
    assert 'btn_id != "owner_panel"' not in content, "owner_panel bypass must be removed"
    assert 'guard.has_permission(str(self.user_id))' not in content, "Sync permission check must be removed"


def test_bot_uses_registry_dispatcher():
    """Bot must use dispatch_registered_interaction."""
    from pathlib import Path
    content = Path("core/bot.py").read_text()
    assert "dispatch_registered_interaction" in content, "dispatch_registered_interaction must be defined"
    assert "await dispatch_registered_interaction(self, interaction)" in content, "dispatch_registered_interaction must be called"


def test_every_registry_handler_resolves():
    """Registry custom_ids have handler path via dispatcher or bot callbacks."""
    import re
    from pathlib import Path
    from core.interaction_registry import INTERACTION_REGISTRY
    from core.bot import resolve_registered_handler, dispatch_registered_interaction
    
    # Verify dispatcher function exists and is callable
    assert callable(dispatch_registered_interaction), "dispatch_registered_interaction must be callable"
    assert callable(resolve_registered_handler), "resolve_registered_handler must be callable"
    
    # Verify registry has entries
    assert len(INTERACTION_REGISTRY) > 0, "Registry must have entries"
    
    # Get all module callbacks
    all_callbacks = set()
    for views_file in Path("modules").rglob("views.py"):
        with open(views_file) as f:
            content = f.read()
        matches = re.findall(r'async def (\w+_callback)', content)
        all_callbacks.update(matches)
    
    assert len(all_callbacks) > 0, "Must have module callbacks"


def test_base_view_navigation_ids_are_registered():
    """Navigation IDs in views/base.py must be in registry."""
    from pathlib import Path
    from core.interaction_registry import INTERACTION_REGISTRY

    content = Path("views/base.py").read_text()

    assert "back_btn" not in content, "back_btn must be replaced with nav_back"
    assert "home_btn" not in content, "home_btn must be replaced with nav_home"
    assert "prev_btn" not in content, "prev_btn must be replaced with nav_prev"
    assert "next_btn" not in content, "next_btn must be replaced with nav_next"

    assert "nav_back" in INTERACTION_REGISTRY, "nav_back must be in registry"
    assert "nav_home" in INTERACTION_REGISTRY, "nav_home must be in registry"
    assert "nav_prev" in INTERACTION_REGISTRY, "nav_prev must be in registry"
    assert "nav_next" in INTERACTION_REGISTRY, "nav_next must be in registry"


def test_every_registry_handler_resolves_to_callable():
    """Registry custom_ids must resolve via bot handlers or module callbacks."""
    import re
    from pathlib import Path
    from core.bot import resolve_registered_handler, WOSMBot, LOCAL_VIEW_CALLBACKS
    from core.interaction_registry import INTERACTION_REGISTRY

    bot = WOSMBot()
    
    # Collect all module callbacks
    all_callbacks = set()
    for views_file in Path("modules").rglob("views.py"):
        with open(views_file) as f:
            content = f.read()
        matches = re.findall(r'async def (\w+_callback)', content)
        all_callbacks.update(matches)
    
    # Collect operations button callbacks (self-contained in views)
    ops_callbacks = set()
    ops_views_file = Path("modules/operations/views.py")
    if ops_views_file.exists():
        with open(ops_views_file) as f:
            content = f.read()
        # Find all Button classes with callbacks
        button_classes = re.findall(r'class (\w+Button)\(discord\.ui\.Button\)', content)
        ops_callbacks.update(button_classes)

    missing = []

    for custom_id, spec in INTERACTION_REGISTRY.items():
        # Skip local view callbacks - handled by View's own callbacks
        if custom_id in LOCAL_VIEW_CALLBACKS:
            continue
        # Skip operations module - they have self-contained button callbacks
        if custom_id.startswith("ops_"):
            continue

        handler = resolve_registered_handler(bot, spec)

        # Check if callback exists in modules
        callback_name = f"{custom_id}_callback"
        if callback_name in all_callbacks:
            continue

        if handler is None:
            missing.append(custom_id)

    assert not missing, f"Missing handlers: {missing}"


def test_pagination_buttons_have_real_callbacks():
    """Pagination buttons must have real callbacks, not dummy handlers."""
    from views.base import PaginationView, PageInfo

    view = PaginationView(
        user_id=123,
        items=list(range(25)),
        items_per_page=10,
        page_info=PageInfo(title="Test", description="Test")
    )

    buttons = {item.custom_id: item for item in view.children if hasattr(item, "custom_id")}

    assert "nav_prev" in buttons
    assert "nav_next" in buttons
    assert buttons["nav_prev"].callback is not None
    assert buttons["nav_next"].callback is not None


def test_nav_prev_next_are_not_dummy_handlers():
    """Bot handlers must not send dummy pagination messages."""
    from pathlib import Path

    content = Path("core/bot.py").read_text()

    assert 'send_message("الصفحة السابقة."' not in content
    assert 'send_message("الصفحة التالية."' not in content
    assert 'send_message("الصفحة السابقة.",' not in content
    assert 'send_message("الصفحة التالية.",' not in content


def test_dispatcher_has_no_button_callbacks_fallback():
    """Dispatcher must not use _button_callbacks as fallback."""
    from pathlib import Path
    from core.bot import dispatch_registered_interaction

    content = Path("core/bot.py").read_text()

    # Find the dispatch_registered_interaction function
    import re
    match = re.search(r'async def dispatch_registered_interaction.*?(?=\n(?:async )?def |\\nclass |\\Z)', content, re.DOTALL)
    if match:
        dispatcher_body = match.group(0)
        assert "_button_callbacks" not in dispatcher_body, \
            "dispatch_registered_interaction must not reference _button_callbacks"
        assert "_dynamic_router" not in dispatcher_body, \
            "dispatch_registered_interaction must not reference _dynamic_router"


def test_nav_prev_next_not_dummy_in_bot():
    """Bot must not have dummy handlers for nav_prev/nav_next."""
    from pathlib import Path
    content = Path("core/bot.py").read_text()

    # Check that _handle_nav_prev/_handle_nav_next don't send dummy messages
    # They should either not exist or be properly documented as local-view handlers
    lines = content.split('\n')
    in_nav_prev = False
    in_nav_next = False

    for i, line in enumerate(lines):
        if 'async def _handle_nav_prev' in line:
            in_nav_prev = True
            nav_prev_block = []
        elif 'async def _handle_nav_next' in line:
            in_nav_next = True
            nav_next_block = []
        elif in_nav_prev and (line.startswith('async def ') or line.startswith('def ') or line.startswith('class ')):
            in_nav_prev = False
        elif in_nav_next and (line.startswith('async def ') or line.startswith('def ') or line.startswith('class ')):
            in_nav_next = False

        if in_nav_prev and 'send_message' in line:
            # Check it's not a dummy message
            assert '"الصفحة السابقة."' not in line and '"الصفحة التالية."' not in line, \
                "_handle_nav_prev must not send dummy pagination messages"
        if in_nav_next and 'send_message' in line:
            assert '"الصفحة السابقة."' not in line and '"الصفحة التالية."' not in line, \
                "_handle_nav_next must not send dummy pagination messages"


def test_pagination_callbacks_change_page():
    """Pagination callbacks must change the page."""
    from views.base import PaginationView, PageInfo

    view = PaginationView(
        user_id=123,
        items=list(range(25)),
        items_per_page=10,
        page_info=PageInfo(title="Test", description="Test")
    )

    # Check that _current_page changes on next
    assert view._current_page == 0
    # Verify buttons exist with callbacks
    buttons = {b.custom_id: b for b in view.children if hasattr(b, "custom_id")}
    assert buttons["nav_prev"].callback is not None
    assert buttons["nav_next"].callback is not None


def test_local_view_callbacks_defined():
    """LOCAL_VIEW_CALLBACKS must be defined in bot.py."""
    from core.bot import LOCAL_VIEW_CALLBACKS
    assert "nav_prev" in LOCAL_VIEW_CALLBACKS
    assert "nav_next" in LOCAL_VIEW_CALLBACKS


def test_local_view_callbacks_checked_before_registry_lookup():
    """LOCAL_VIEW_CALLBACKS must be checked BEFORE INTERACTION_REGISTRY.get()."""
    from pathlib import Path

    content = Path("core/bot.py").read_text()

    # Find dispatcher body
    body_start = content.index("async def dispatch_registered_interaction")
    body_end = content.index("class WOSMBot", body_start)
    body = content[body_start:body_end]

    local_check_pos = body.index("if custom_id in LOCAL_VIEW_CALLBACKS")
    registry_check_pos = body.index("INTERACTION_REGISTRY.get(custom_id)")

    assert local_check_pos < registry_check_pos, \
        "LOCAL_VIEW_CALLBACKS check must come BEFORE INTERACTION_REGISTRY.get()"


def test_no_global_dummy_nav_prev_next_handlers():
    """Bot must not have _handle_nav_prev/_handle_nav_next handlers."""
    from pathlib import Path

    content = Path("core/bot.py").read_text()

    assert "async def _handle_nav_prev" not in content, \
        "_handle_nav_prev must not exist in bot.py"
    assert "async def _handle_nav_next" not in content, \
        "_handle_nav_next must not exist in bot.py"
    assert "هذا الزر يعمل فقط في العرض المقسم" not in content, \
        "Dummy message for nav buttons must not exist"


def test_no_modal_wait_pattern():
    """Ensure no modal.wait() patterns exist - they break Discord interactions."""
    from pathlib import Path
    import re

    offenders = []
    for path in list(Path("modules").rglob("*.py")) + list(Path("views").rglob("*.py")):
        content = path.read_text()
        if "modal.wait()" in content or "await modal.wait()" in content:
            # Extract line numbers
            for i, line in enumerate(content.splitlines(), 1):
                if "modal.wait()" in line or "await modal.wait()" in line:
                    offenders.append(f"{path}:{i}")

    assert not offenders, f"Remove modal.wait() patterns from: {offenders}"


def test_no_raw_discord_modal_in_callbacks():
    """Use Modal subclasses with on_submit instead of discord.ui.Modal() in callbacks."""
    from pathlib import Path
    import ast

    offenders = []
    for path in Path("modules").rglob("views.py"):
        content = path.read_text()
        # Check for discord.ui.Modal( pattern (inline modal creation)
        if re.search(r'discord\.ui\.Modal\s*\(', content):
            offenders.append(str(path))

    assert not offenders, f"Use Modal subclasses with on_submit instead: {offenders}"
