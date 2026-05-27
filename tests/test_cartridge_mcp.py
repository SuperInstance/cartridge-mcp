"""Tests for cartridge_mcp package."""

from cartridge_mcp.cartridge import Cartridge, ToolDefinition, OnboardingInfo
from cartridge_mcp.skin import Skin, SkinTransform
from cartridge_mcp.inventory import InventoryManager
from cartridge_mcp.lifecycle import LifecycleManager, CartridgeState, Scene
from cartridge_mcp.health import HealthMonitor, HealthStatus
from cartridge_mcp.server import MCPServer

import asyncio
import json
import os
import tempfile
from pathlib import Path


def _run_async(coro):
    """Run an async coroutine synchronously (works in all Python 3.10+)."""
    return asyncio.run(coro)

# ══════════════════════════════════════════════════════════
# Cartridge tests
# ══════════════════════════════════════════════════════════

class TestToolDefinition:
    def test_from_dict(self):
        td = ToolDefinition.from_dict({
            "name": "my_tool",
            "description": "Does stuff",
            "inputSchema": {"type": "object", "properties": {"x": {"type": "string"}}},
        })
        assert td.name == "my_tool"
        assert td.description == "Does stuff"
        assert td.input_schema == {"type": "object", "properties": {"x": {"type": "string"}}}
        assert td.roles == ("default",)

    def test_to_dict_roundtrip(self):
        td = ToolDefinition(name="t", description="d", input_schema={"type": "object"})
        d = td.to_dict()
        assert d["name"] == "t"
        td2 = ToolDefinition.from_dict(d)
        assert td2.name == td.name
        assert td2.description == td.description

    def test_from_dict_with_roles(self):
        td = ToolDefinition.from_dict({"name": "x", "roles": ["talker", "doer"]})
        assert td.roles == ("talker", "doer")


class TestOnboardingInfo:
    def test_from_dict(self):
        ob = OnboardingInfo.from_dict({
            "greeting": "Hello!",
            "description": "A thing",
            "tools": ["tool1", "tool2"],
            "usage": "Use it",
        })
        assert ob.greeting == "Hello!"
        assert ob.tools == ("tool1", "tool2")

    def test_from_dict_none(self):
        ob = OnboardingInfo.from_dict(None)
        assert ob.greeting == ""
        assert ob.tools == ()

    def test_to_dict_roundtrip(self):
        ob = OnboardingInfo(greeting="Hi", description="desc", tools=("a", "b"))
        d = ob.to_dict()
        assert d["greeting"] == "Hi"
        assert d["tools"] == ["a", "b"]


class TestCartridge:
    def _sample_manifest(self):
        return {
            "id": "test-cart",
            "name": "Test Cartridge",
            "version": "1.0.0",
            "description": "A test cartridge",
            "tools": [
                {"name": "do_thing", "description": "Does the thing", "inputSchema": {"type": "object"}},
                {"name": "check_status", "description": "Checks status"},
            ],
            "onboarding": {
                "human": {"greeting": "Hi human!", "tools": ["do_thing"]},
                "agent": {"greeting": "Agent ready.", "tools": ["do_thing", "check_status"]},
            },
            "tags": ["test", "example"],
            "repo": "https://example.com/test",
        }

    def test_from_manifest(self):
        cart = Cartridge.from_manifest(self._sample_manifest())
        assert cart.id == "test-cart"
        assert cart.name == "Test Cartridge"
        assert cart.version == "1.0.0"
        assert len(cart.tools) == 2
        assert cart.tools[0].name == "do_thing"
        assert cart.tags == ("test", "example")

    def test_get_onboarding_human(self):
        cart = Cartridge.from_manifest(self._sample_manifest())
        ob = cart.get_onboarding("human")
        assert ob.greeting == "Hi human!"
        assert ob.tools == ("do_thing",)

    def test_get_onboarding_agent(self):
        cart = Cartridge.from_manifest(self._sample_manifest())
        ob = cart.get_onboarding("agent")
        assert ob.greeting == "Agent ready."
        assert len(ob.tools) == 2

    def test_get_onboarding_default(self):
        cart = Cartridge(id="x", name="X")
        ob = cart.get_onboarding("human")
        assert "X" in ob.greeting
        assert ob.tools == ()

    def test_tool_names(self):
        cart = Cartridge.from_manifest(self._sample_manifest())
        assert cart.tool_names == ["do_thing", "check_status"]

    def test_summary(self):
        cart = Cartridge.from_manifest(self._sample_manifest())
        s = cart.summary()
        assert s["id"] == "test-cart"
        assert s["tools"] == 2

    def test_manifest_roundtrip(self):
        original = self._sample_manifest()
        cart = Cartridge.from_manifest(original)
        m = cart.manifest
        assert m["id"] == "test-cart"
        assert m["name"] == "Test Cartridge"

    def test_repr(self):
        cart = Cartridge(id="x", name="X", version="0.1.0")
        assert "x" in repr(cart)


# ══════════════════════════════════════════════════════════
# Skin tests
# ══════════════════════════════════════════════════════════

class TestSkinTransform:
    def test_apply_prefix_suffix(self):
        t = SkinTransform(prefix="[hi] ", suffix=" [bye]")
        assert t.apply("text") == "[hi] text [bye]"

    def test_apply_replacements(self):
        t = SkinTransform(replacements={"Error": "WHOOPS", "OK": "NICE"})
        assert t.apply("Error: OK") == "WHOOPS: NICE"

    def test_apply_empty(self):
        t = SkinTransform()
        assert t.apply("hello") == "hello"

    def test_from_dict_none(self):
        t = SkinTransform.from_dict(None)
        assert t.prefix == ""


class TestSkin:
    def test_from_dict(self):
        s = Skin.from_dict({
            "id": "test-skin",
            "name": "Test Skin",
            "description": "A test skin",
            "archetype": "Test",
            "transforms": {
                "default": {"prefix": "[mode] "},
                "tool": {"prefix": "[tool] ", "replacements": {"Error": "BORK"}},
            },
        })
        assert s.id == "test-skin"
        assert s.name == "Test Skin"
        assert "default" in s.transforms
        assert "tool" in s.transforms

    def test_apply_default(self):
        s = Skin.from_dict({
            "id": "x", "name": "X",
            "transforms": {"default": {"prefix": "[x] "}},
        })
        assert s.apply("hello") == "[x] hello"

    def test_apply_with_role(self):
        s = Skin.from_dict({
            "id": "x", "name": "X",
            "transforms": {
                "default": {"prefix": "[def] "},
                "tool": {"prefix": "[tool] "},
            },
        })
        assert s.apply("hello", role="tool") == "[tool] hello"

    def test_apply_fallback_to_default(self):
        s = Skin.from_dict({
            "id": "x", "name": "X",
            "transforms": {"default": {"prefix": "[def] "}},
        })
        assert s.apply("hello", role="nonexistent") == "[def] hello"

    def test_apply_with_system_prompt(self):
        s = Skin.from_dict({
            "id": "x", "name": "My Skin",
            "transforms": {"default": {"systemPrompt": "be funny"}},
        })
        result = s.apply("hello")
        assert "My Skin mode: be funny" in result
        assert "hello" in result

    def test_apply_no_transform(self):
        s = Skin(id="x", name="X", transforms={})
        assert s.apply("hello") == "hello"

    def test_summary(self):
        s = Skin(id="x", name="X", description="d", archetype="a")
        assert s.summary() == {"id": "x", "name": "X", "description": "d", "archetype": "a"}


# ══════════════════════════════════════════════════════════
# Inventory tests
# ══════════════════════════════════════════════════════════

class TestInventoryManager:
    def test_builtin_cartridges(self):
        inv = InventoryManager()
        assert "spreader-loop" in inv.cartridges
        assert "oracle-relay" in inv.cartridges
        assert "fleet-guardian" in inv.cartridges
        assert len(inv.cartridges) == 3

    def test_builtin_skins(self):
        inv = InventoryManager()
        assert "straight-man" in inv.skins
        assert "sarcastic-build" in inv.skins
        assert "none" in inv.skins
        assert len(inv.skins) == 8

    def test_get_cartridge(self):
        inv = InventoryManager()
        cart = inv.get_cartridge("spreader-loop")
        assert cart is not None
        assert cart.name == "Spreader Loop"

    def test_get_cartridge_missing(self):
        inv = InventoryManager()
        assert inv.get_cartridge("nonexistent") is None

    def test_get_skin(self):
        inv = InventoryManager()
        skin = inv.get_skin("rivals")
        assert skin is not None
        assert skin.name == "Rivals Mode"

    def test_list_cartridges(self):
        inv = InventoryManager()
        carts = inv.list_cartridges()
        assert len(carts) == 3
        assert all(isinstance(c, Cartridge) for c in carts)

    def test_list_skins(self):
        inv = InventoryManager()
        skins = inv.list_skins()
        assert len(skins) == 8

    def test_load_cartridge_dir(self):
        inv = InventoryManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            cart_dir = Path(tmpdir) / "my-cart"
            cart_dir.mkdir()
            (cart_dir / "cartridge.json").write_text(json.dumps({
                "id": "my-cart",
                "name": "My Cart",
                "version": "0.1.0",
                "description": "Custom",
                "tools": [{"name": "custom_tool", "description": "Does custom things"}],
            }))
            count = inv.load_cartridge_dir(tmpdir)
            assert count == 1
            assert "my-cart" in inv.cartridges
            assert inv.cartridges["my-cart"].name == "My Cart"

    def test_load_cartridge_dir_empty(self):
        inv = InventoryManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            count = inv.load_cartridge_dir(tmpdir)
            assert count == 0

    def test_load_cartridge_dir_missing(self):
        inv = InventoryManager()
        path = "/tmp/nonexistent_cart_dir_test_12345"
        count = inv.load_cartridge_dir(path)
        assert count == 0
        assert Path(path).exists()  # created

    def test_load_skin_dir(self):
        inv = InventoryManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            skin_path = Path(tmpdir) / "cool-skin.json"
            skin_path.write_text(json.dumps({
                "id": "cool-skin",
                "name": "Cool Skin",
                "transforms": {"default": {"prefix": "[cool] "}},
            }))
            count = inv.load_skin_dir(tmpdir)
            assert count == 1
            assert "cool-skin" in inv.skins

    def test_load_cartridge_bad_json(self):
        inv = InventoryManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            cart_dir = Path(tmpdir) / "bad-cart"
            cart_dir.mkdir()
            (cart_dir / "cartridge.json").write_text("not json")
            count = inv.load_cartridge_dir(tmpdir)
            assert count == 0

    def test_refresh(self):
        inv = InventoryManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            inv.load_cartridge_dir(tmpdir)
            # Add a new cartridge after initial load
            cart_dir = Path(tmpdir) / "late-cart"
            cart_dir.mkdir()
            (cart_dir / "cartridge.json").write_text(json.dumps({
                "id": "late-cart", "name": "Late", "tools": [],
            }))
            inv.refresh()
            assert "late-cart" in inv.cartridges


# ══════════════════════════════════════════════════════════
# Lifecycle tests
# ══════════════════════════════════════════════════════════

class TestLifecycleManager:
    def test_initial_state(self):
        lm = LifecycleManager()
        assert lm.state == CartridgeState.EMPTY
        assert lm.active_cartridge_id is None
        assert lm.active_skin_id is None
        assert lm.scene is None

    def test_load(self):
        lm = LifecycleManager()
        cart = lm.load("spreader-loop")
        assert cart.id == "spreader-loop"
        assert lm.state == CartridgeState.ACTIVE
        assert lm.active_cartridge_id == "spreader-loop"

    def test_load_missing(self):
        lm = LifecycleManager()
        try:
            lm.load("nonexistent")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass

    def test_unload(self):
        lm = LifecycleManager()
        lm.load("spreader-loop")
        cart = lm.unload()
        assert cart is not None
        assert cart.id == "spreader-loop"
        assert lm.state == CartridgeState.EMPTY
        assert lm.active_cartridge_id is None

    def test_unload_when_empty(self):
        lm = LifecycleManager()
        result = lm.unload()
        assert result is None

    def test_swap(self):
        lm = LifecycleManager()
        lm.load("spreader-loop")
        result = lm.swap("oracle-relay")
        assert result["old"]["id"] == "spreader-loop"
        assert result["new"]["id"] == "oracle-relay"
        assert lm.active_cartridge_id == "oracle-relay"

    def test_apply_skin(self):
        lm = LifecycleManager()
        lm.load("spreader-loop")
        skin = lm.apply_skin("rivals")
        assert skin.id == "rivals"
        assert lm.active_skin_id == "rivals"

    def test_apply_skin_missing(self):
        lm = LifecycleManager()
        try:
            lm.apply_skin("nonexistent")
            assert False
        except KeyError:
            pass

    def test_remove_skin(self):
        lm = LifecycleManager()
        lm.load("spreader-loop")
        lm.apply_skin("rivals")
        removed = lm.remove_skin()
        assert removed == "rivals"
        assert lm.active_skin_id is None

    def test_remove_skin_when_none(self):
        lm = LifecycleManager()
        assert lm.remove_skin() is None

    def test_build_scene(self):
        lm = LifecycleManager()
        scene = lm.build_scene("fleet-guardian", skin_id="sarcastic-build", roles={"primary": "sarcastic-build"})
        assert scene.cartridge_id == "fleet-guardian"
        assert scene.skin_id == "sarcastic-build"
        assert scene.roles == {"primary": "sarcastic-build"}
        assert len(scene.tools) == 4  # guardian has 4 tools

    def test_build_scene_with_skin_transform(self):
        lm = LifecycleManager()
        scene = lm.build_scene("fleet-guardian", skin_id="sarcastic-build")
        # Tool descriptions should have skin applied
        for t in scene.tools:
            # sarcastic-build's tool prefix is "[sigh] "
            assert t["description"].startswith("[sigh] ")

    def test_build_scene_default_skin(self):
        lm = LifecycleManager()
        # spreader-loop has no default skin
        scene = lm.build_scene("spreader-loop")
        assert scene.skin_id is None

    def test_build_scene_missing_cartridge(self):
        lm = LifecycleManager()
        try:
            lm.build_scene("nonexistent")
            assert False
        except KeyError:
            pass

    def test_active_cartridge_property(self):
        lm = LifecycleManager()
        assert lm.active_cartridge is None
        lm.load("spreader-loop")
        assert lm.active_cartridge is not None
        assert lm.active_cartridge.id == "spreader-loop"

    def test_active_skin_property(self):
        lm = LifecycleManager()
        assert lm.active_skin is None
        lm.load("spreader-loop")
        lm.apply_skin("rivals")
        assert lm.active_skin is not None
        assert lm.active_skin.id == "rivals"

    def test_status(self):
        lm = LifecycleManager()
        lm.load("spreader-loop")
        status = lm.status()
        assert status["state"] == "active"
        assert status["cartridge"]["id"] == "spreader-loop"
        assert status["skin"] is None

    def test_history(self):
        lm = LifecycleManager()
        lm.load("spreader-loop")
        lm.apply_skin("rivals")
        lm.unload()
        history = lm.history()
        assert len(history) == 3
        assert history[0]["action"] == "load"
        assert history[1]["action"] == "skin_apply"
        assert history[2]["action"] == "unload"

    def test_history_limit(self):
        lm = LifecycleManager()
        for _ in range(5):
            lm.load("spreader-loop")
            lm.unload()
        history = lm.history(limit=3)
        assert len(history) == 3


# ══════════════════════════════════════════════════════════
# Health tests
# ══════════════════════════════════════════════════════════

class TestHealthMonitor:
    def test_healthy_empty(self):
        lm = LifecycleManager()
        hm = HealthMonitor(lifecycle=lm)
        check = hm.check_all()
        assert check.status == HealthStatus.HEALTHY

    def test_healthy_with_cartridge(self):
        lm = LifecycleManager()
        lm.load("spreader-loop")
        hm = HealthMonitor(lifecycle=lm)
        check = hm.check_all()
        assert check.status == HealthStatus.HEALTHY

    def test_cartridge_state_check(self):
        lm = LifecycleManager()
        lm.load("spreader-loop")
        hm = HealthMonitor(lifecycle=lm)
        check = hm.check_cartridge_state()
        assert check.status == HealthStatus.HEALTHY
        assert "spreader-loop" in check.message

    def test_inventory_check(self):
        lm = LifecycleManager()
        hm = HealthMonitor(lifecycle=lm)
        check = hm.check_inventory()
        assert check.status == HealthStatus.HEALTHY
        assert check.details["cartridges"] == 3
        assert check.details["skins"] == 8

    def test_scene_consistency(self):
        lm = LifecycleManager()
        lm.build_scene("spreader-loop", skin_id="rivals")
        hm = HealthMonitor(lifecycle=lm)
        check = hm.check_scene()
        assert check.status == HealthStatus.HEALTHY

    def test_recent_checks(self):
        lm = LifecycleManager()
        hm = HealthMonitor(lifecycle=lm)
        hm.check_all()
        hm.check_all()
        assert len(hm.recent_checks()) == 6  # 2 checks × 3 subchecks


# ══════════════════════════════════════════════════════════
# Server tests
# ══════════════════════════════════════════════════════════

class TestMCPServer:
    def _make_request(self, method: str, params: dict | None = None, req_id: int = 1) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }

    def test_initialize(self):
        server = MCPServer()
        resp = _run_async(server.handle_request(self._make_request("initialize")))
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert resp["result"]["serverInfo"]["name"] == "cartridge-mcp"
        assert resp["result"]["serverInfo"]["cartridges"] == 3

    def test_ping(self):
        server = MCPServer()
        resp = _run_async(server.handle_request(self._make_request("ping")))
        assert resp["result"]["pong"] is True

    def test_invalid_jsonrpc(self):
        server = MCPServer()
        resp = _run_async(server.handle_request({"jsonrpc": "1.0", "id": 1, "method": "ping"}))
        assert "error" in resp
        assert resp["error"]["code"] == -32600

    def test_method_not_found(self):
        server = MCPServer()
        resp = _run_async(server.handle_request(self._make_request("nonexistent/method")))
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_tools_list(self):
        server = MCPServer()
        resp = _run_async(server.handle_request(self._make_request("tools/list")))
        tools = resp["result"]["tools"]
        names = [t["name"] for t in tools]
        assert "cartridge_list" in names
        assert "scene_build" in names
        assert "health_check" in names

    def test_tools_list_with_active_cartridge(self):
        server = MCPServer()
        server.lifecycle.load("spreader-loop")
        resp = _run_async(server.handle_request(self._make_request("tools/list")))
        tools = resp["result"]["tools"]
        names = [t["name"] for t in tools]
        assert "spreader_run" in names
        assert "spreader_status" in names

    def test_tool_cartridge_list(self):
        server = MCPServer()
        resp = _run_async(server.handle_request(self._make_request("tools/call", {"name": "cartridge_list"})))
        text = resp["result"]["content"][0]["text"]
        data = json.loads(text)
        assert len(data) == 3
        ids = [d["id"] for d in data]
        assert "spreader-loop" in ids

    def test_tool_cartridge_load(self):
        server = MCPServer()
        resp = _run_async(server.handle_request(self._make_request("tools/call", {"name": "cartridge_load", "arguments": {"id": "oracle-relay"}})))
        text = resp["result"]["content"][0]["text"]
        data = json.loads(text)
        assert data["loaded"] == "oracle-relay"
        assert "bottle_send" in data["tools"]

    def test_tool_cartridge_load_missing(self):
        server = MCPServer()
        resp = _run_async(server.handle_request(self._make_request("tools/call", {"name": "cartridge_load", "arguments": {"id": "nope"}})))
        assert "error" in resp
        assert resp["error"]["code"] == -404

    def test_tool_cartridge_onboard(self):
        server = MCPServer()
        resp = _run_async(server.handle_request(self._make_request("tools/call", {
            "name": "cartridge_onboard",
            "arguments": {"id": "fleet-guardian", "audience": "agent"},
        })))
        text = resp["result"]["content"][0]["text"]
        data = json.loads(text)
        assert "Watchdog" in data["greeting"]

    def test_tool_skin_list(self):
        server = MCPServer()
        resp = _run_async(server.handle_request(self._make_request("tools/call", {"name": "skin_list"})))
        text = resp["result"]["content"][0]["text"]
        data = json.loads(text)
        assert len(data) == 8

    def test_tool_skin_apply(self):
        server = MCPServer()
        server.lifecycle.load("spreader-loop")
        resp = _run_async(server.handle_request(self._make_request("tools/call", {"name": "skin_apply", "arguments": {"id": "rivals"}})))
        text = resp["result"]["content"][0]["text"]
        data = json.loads(text)
        assert data["applied"] == "rivals"

    def test_tool_scene_build(self):
        server = MCPServer()
        resp = _run_async(server.handle_request(self._make_request("tools/call", {
            "name": "scene_build",
            "arguments": {"cartridge": "spreader-loop", "skin": "field-journal", "roles": {"worker": "field-journal"}},
        })))
        text = resp["result"]["content"][0]["text"]
        data = json.loads(text)
        assert data["cartridge"] == "spreader-loop"
        assert data["skin"] == "field-journal"
        assert "spreader_run" in data["tools"]

    def test_tool_scene_status(self):
        server = MCPServer()
        resp = _run_async(server.handle_request(self._make_request("tools/call", {"name": "scene_status"})))
        text = resp["result"]["content"][0]["text"]
        data = json.loads(text)
        assert data["status"] == "no scene loaded"

    def test_tool_health_check(self):
        server = MCPServer()
        resp = _run_async(server.handle_request(self._make_request("tools/call", {"name": "health_check"})))
        text = resp["result"]["content"][0]["text"]
        data = json.loads(text)
        assert data["status"] == "healthy"

    def test_tool_delegation(self):
        server = MCPServer()
        server.lifecycle.load("spreader-loop")
        resp = _run_async(server.handle_request(self._make_request("tools/call", {
            "name": "spreader_run",
            "arguments": {"task": "test", "target": "/tmp"},
        })))
        text = resp["result"]["content"][0]["text"]
        data = json.loads(text)
        assert data["status"] == "delegated"
        assert data["cartridge"] == "spreader-loop"

    def test_tool_unknown(self):
        server = MCPServer()
        resp = _run_async(server.handle_request(self._make_request("tools/call", {"name": "fake_tool"})))
        assert "error" in resp

    def test_scene_export(self):
        server = MCPServer()
        server.lifecycle.load("spreader-loop")
        resp = _run_async(server.handle_request(self._make_request("tools/call", {"name": "scene_export"})))
        text = resp["result"]["content"][0]["text"]
        data = json.loads(text)
        assert "exported" in data
        assert data["cartridge_manifest"]["id"] == "spreader-loop"

    def test_load_cartridge_dir(self):
        server = MCPServer()
        with tempfile.TemporaryDirectory() as tmpdir:
            cart_dir = Path(tmpdir) / "ext-cart"
            cart_dir.mkdir()
            (cart_dir / "cartridge.json").write_text(json.dumps({
                "id": "ext-cart", "name": "External", "tools": [{"name": "ext_tool", "description": "External tool"}],
            }))
            count = server.load_cartridge_dir(tmpdir)
            assert count == 1
            assert "ext-cart" in server.inventory.cartridges
