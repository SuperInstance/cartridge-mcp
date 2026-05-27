"""MCPServer — JSON-RPC server implementing the Model Context Protocol for cartridges."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Any

from .health import HealthMonitor
from .lifecycle import LifecycleManager
from .inventory import InventoryManager

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2024-11-05"


@dataclass
class MCPServer:
    """MCP server for swappable behavior cartridges.

    Handles JSON-RPC 2.0 requests over stdio. Supports the standard MCP
    methods (initialize, tools/list, tools/call) plus cartridge-specific
    extensions for cartridge management, skin application, and scene building.
    """

    version: str = "0.2.0"
    inventory: InventoryManager = field(default_factory=InventoryManager)
    lifecycle: LifecycleManager = field(init=False)
    health: HealthMonitor = field(init=False)

    def __post_init__(self) -> None:
        self.lifecycle = LifecycleManager(inventory=self.inventory)
        self.health = HealthMonitor(lifecycle=self.lifecycle)

    # ── Configuration ─────────────────────────────────────

    def load_cartridge_dir(self, path: str) -> int:
        """Load cartridges from a directory."""
        count = self.inventory.load_cartridge_dir(path)
        self.lifecycle.inventory = self.inventory
        return count

    def load_skin_dir(self, path: str) -> int:
        """Load skins from a directory."""
        count = self.inventory.load_skin_dir(path)
        self.lifecycle.inventory = self.inventory
        return count

    # ── Request handling ──────────────────────────────────

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle an incoming JSON-RPC 2.0 request."""
        request_id = request.get("id")

        if request.get("jsonrpc") != "2.0":
            return self._error(request_id, -32600, "Invalid Request")

        method = request.get("method", "")
        params = request.get("params", {})

        handler = {
            "initialize": self._initialize,
            "tools/list": self._list_tools,
            "tools/call": self._call_tool,
            "ping": lambda p: {"pong": True, "version": self.version},
        }.get(method)

        if handler is None:
            return self._error(request_id, -32601, f"Method not found: {method}")

        try:
            result = handler(params)
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except KeyError as exc:
            return self._error(request_id, -404, str(exc))
        except Exception as exc:
            logger.exception("Error handling %s", method)
            return self._error(request_id, -32603, str(exc))

    # ── Method implementations ────────────────────────────

    def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": True},
                "experimental": {"cartridges": True, "skins": True, "scenes": True},
            },
            "serverInfo": {
                "name": "cartridge-mcp",
                "version": self.version,
                "cartridges": len(self.inventory.cartridges),
                "skins": len(self.inventory.skins),
            },
        }

    def _list_tools(self, params: dict[str, Any]) -> dict[str, Any]:
        """List all available tools — management + active cartridge tools."""
        tools: list[dict[str, Any]] = [
            {"name": "cartridge_list", "description": "List all available cartridges with metadata",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "cartridge_load", "description": "Load a cartridge by ID, making its tools available",
             "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
            {"name": "cartridge_onboard", "description": "Get onboarding info for a cartridge",
             "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "audience": {"type": "string", "enum": ["human", "agent"], "default": "human"}}, "required": ["id"]}},
            {"name": "skin_list", "description": "List all available personality skins",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "skin_apply", "description": "Apply a personality skin to the active cartridge",
             "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
            {"name": "scene_build", "description": "Build a scene with cartridge + skin + role assignments",
             "inputSchema": {"type": "object", "properties": {"cartridge": {"type": "string"}, "skin": {"type": "string"}, "roles": {"type": "object"}}, "required": ["cartridge"]}},
            {"name": "scene_status", "description": "Get current scene configuration",
             "inputSchema": {"type": "object", "properties": {}}},
            {"name": "scene_export", "description": "Export current scene as shareable JSON",
             "inputSchema": {"type": "object", "properties": {"format": {"type": "string", "enum": ["json", "cartridge"], "default": "cartridge"}}}},
            {"name": "health_check", "description": "Run system health check",
             "inputSchema": {"type": "object", "properties": {}}},
        ]

        # Active cartridge tools
        cart = self.lifecycle.active_cartridge
        if cart:
            skin = self.lifecycle.active_skin
            for t in cart.tools:
                desc = t.description
                if skin:
                    desc = skin.apply(desc, role="tool")
                tools.append({"name": t.name, "description": desc, "inputSchema": t.input_schema})

        return {"tools": tools}

    def _call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        """Call a tool by name with arguments."""
        name = params.get("name", "")
        args = params.get("arguments", {})

        handlers: dict[str, Any] = {
            "cartridge_list": self._tool_cartridge_list,
            "cartridge_load": self._tool_cartridge_load,
            "cartridge_onboard": self._tool_cartridge_onboard,
            "skin_list": self._tool_skin_list,
            "skin_apply": self._tool_skin_apply,
            "scene_build": self._tool_scene_build,
            "scene_status": self._tool_scene_status,
            "scene_export": self._tool_scene_export,
            "health_check": self._tool_health_check,
        }

        handler = handlers.get(name)
        if handler:
            return {"content": [{"type": "text", "text": json.dumps(handler(args), indent=2)}]}

        # Delegate to active cartridge tools
        cart = self.lifecycle.active_cartridge
        if cart and name in cart.tool_names:
            return {"content": [{"type": "text", "text": json.dumps({
                "cartridge": cart.id,
                "tool": name,
                "args": args,
                "status": "delegated",
                "note": "Tool execution handled by cartridge implementation",
            })}]}

        raise KeyError(f"Unknown tool: {name}")

    # ── Tool implementations ──────────────────────────────

    def _tool_cartridge_list(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        return [c.summary() for c in self.inventory.list_cartridges()]

    def _tool_cartridge_load(self, args: dict[str, Any]) -> dict[str, Any]:
        cart = self.lifecycle.load(args["id"])
        return {
            "loaded": cart.id,
            "name": cart.name,
            "version": cart.version,
            "description": cart.description,
            "tools": cart.tool_names,
        }

    def _tool_cartridge_onboard(self, args: dict[str, Any]) -> dict[str, Any]:
        cart = self.inventory.get_cartridge(args["id"])
        if cart is None:
            raise KeyError(f"Cartridge not found: {args['id']}")
        ob = cart.get_onboarding(args.get("audience", "human"))
        return ob.to_dict()

    def _tool_skin_list(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        return [s.summary() for s in self.inventory.list_skins()]

    def _tool_skin_apply(self, args: dict[str, Any]) -> dict[str, Any]:
        skin = self.lifecycle.apply_skin(args["id"])
        cart = self.lifecycle.active_cartridge
        return {
            "applied": skin.id,
            "name": skin.name,
            "archetype": skin.archetype,
            "to_cartridge": cart.id if cart else None,
        }

    def _tool_scene_build(self, args: dict[str, Any]) -> dict[str, Any]:
        scene = self.lifecycle.build_scene(
            cartridge_id=args["cartridge"],
            skin_id=args.get("skin"),
            roles=args.get("roles"),
        )
        return {
            "scene": scene.cartridge_name,
            "cartridge": scene.cartridge_id,
            "skin": scene.skin_id,
            "roles": scene.roles,
            "tools": [t["name"] for t in scene.tools],
        }

    def _tool_scene_status(self, args: dict[str, Any]) -> dict[str, Any]:
        scene = self.lifecycle.scene
        if scene:
            return scene.to_dict()
        return {"status": "no scene loaded"}

    def _tool_scene_export(self, args: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "scene": self.lifecycle.scene.to_dict() if self.lifecycle.scene else None,
            "exported": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
        cart = self.lifecycle.active_cartridge
        if cart:
            result["cartridge_manifest"] = cart.manifest
        skin = self.lifecycle.active_skin
        if skin:
            result["skin"] = skin.summary()
        return result

    def _tool_health_check(self, args: dict[str, Any]) -> dict[str, Any]:
        check = self.health.check_all()
        return {
            "status": check.status.value,
            "message": check.message,
            "details": check.details,
        }

    # ── Helpers ────────────────────────────────────────────

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    # ── Stdio runner ───────────────────────────────────────

    def run_stdio(self) -> None:
        """Run the server on stdio (JSON-RPC over newline-delimited messages)."""
        logger.info("cartridge-mcp v%s starting (stdio mode)", self.version)
        logger.info("Cartridges: %s", ", ".join(self.inventory.cartridges.keys()))
        logger.info("Skins: %s", ", ".join(self.inventory.skins.keys()))

        import asyncio

        async def _process_line(line: str) -> None:
            line = line.strip()
            if not line:
                return
            try:
                request = json.loads(line)
            except json.JSONDecodeError as exc:
                sys.stderr.write(f"Parse error: {exc}\n")
                return

            response = await self.handle_request(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

        async def _main() -> None:
            loop = asyncio.get_event_loop()
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await loop.connect_read_pipe(lambda: protocol, sys.stdin)

            while True:
                line = await reader.readline()
                if not line:
                    break
                await _process_line(line.decode("utf-8"))

        asyncio.run(_main())
