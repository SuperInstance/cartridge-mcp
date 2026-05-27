"""LifecycleManager — handles load, unload, swap of cartridges with state tracking."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .cartridge import Cartridge
from .inventory import InventoryManager
from .skin import Skin

logger = logging.getLogger(__name__)


class CartridgeState(Enum):
    """Lifecycle state of a cartridge slot."""

    EMPTY = "empty"
    LOADING = "loading"
    ACTIVE = "active"
    UNLOADING = "unloading"
    ERROR = "error"


@dataclass(frozen=True)
class Scene:
    """A fully configured scene: cartridge + skin + role assignments."""

    cartridge_id: str
    cartridge_name: str
    skin_id: str | None = None
    roles: dict[str, str] = field(default_factory=dict)
    tools: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cartridge": self.cartridge_id,
            "name": self.cartridge_name,
            "skin": self.skin_id,
            "roles": self.roles,
            "tools": self.tools,
            "created_at": self.created_at,
        }


@dataclass
class LifecycleManager:
    """Manages the lifecycle of cartridge loading, skin application, and scene building.

    The lifecycle manager is the stateful core — it tracks what's active,
    handles transitions between cartridges, applies skins, and builds scenes.
    """

    inventory: InventoryManager = field(default_factory=InventoryManager)

    # ── Active state ──────────────────────────────────────

    active_cartridge_id: str | None = None
    active_skin_id: str | None = None
    state: CartridgeState = CartridgeState.EMPTY
    scene: Scene | None = None
    _error_message: str | None = None
    _history: list[dict[str, Any]] = field(default_factory=list)

    # ── Cartridge operations ───────────────────────────────

    def load(self, cartridge_id: str) -> Cartridge:
        """Load a cartridge by ID. Raises KeyError if not found."""
        cart = self.inventory.get_cartridge(cartridge_id)
        if cart is None:
            raise KeyError(f"Cartridge not found: {cartridge_id}")

        self.state = CartridgeState.LOADING
        try:
            self.active_cartridge_id = cartridge_id
            # Apply default skin if cartridge has one
            if cart.default_skin:
                self.active_skin_id = cart.default_skin
            self.state = CartridgeState.ACTIVE
            self._record("load", cartridge_id=cartridge_id)
            logger.info("Loaded cartridge: %s v%s", cart.id, cart.version)
            return cart
        except Exception as exc:
            self.state = CartridgeState.ERROR
            self._error_message = str(exc)
            raise

    def unload(self) -> Cartridge | None:
        """Unload the active cartridge. Returns the unloaded cartridge or None."""
        if self.active_cartridge_id is None:
            return None

        cart = self.inventory.get_cartridge(self.active_cartridge_id)
        old_id = self.active_cartridge_id

        self.state = CartridgeState.UNLOADING
        self.active_cartridge_id = None
        self.active_skin_id = None
        self.scene = None
        self.state = CartridgeState.EMPTY
        self._record("unload", cartridge_id=old_id)

        return cart

    def swap(self, new_cartridge_id: str) -> dict[str, Any]:
        """Swap the active cartridge for a new one atomically.

        Returns dict with old and new cartridge info.
        """
        old_id = self.active_cartridge_id
        old_cart = self.inventory.get_cartridge(old_id) if old_id else None

        self.unload()
        new_cart = self.load(new_cartridge_id)

        result = {
            "old": old_cart.summary() if old_cart else None,
            "new": new_cart.summary(),
        }
        self._record("swap", old_id=old_id, new_id=new_cartridge_id)
        return result

    # ── Skin operations ────────────────────────────────────

    def apply_skin(self, skin_id: str) -> Skin:
        """Apply a skin. Raises KeyError if not found."""
        skin = self.inventory.get_skin(skin_id)
        if skin is None:
            raise KeyError(f"Skin not found: {skin_id}")
        self.active_skin_id = skin_id
        self._record("skin_apply", skin_id=skin_id)
        return skin

    def remove_skin(self) -> str | None:
        """Remove the active skin. Returns the removed skin ID."""
        old = self.active_skin_id
        self.active_skin_id = None
        if old:
            self._record("skin_remove", skin_id=old)
        return old

    # ── Scene operations ───────────────────────────────────

    def build_scene(
        self,
        cartridge_id: str,
        skin_id: str | None = None,
        roles: dict[str, str] | None = None,
    ) -> Scene:
        """Build a scene combining cartridge + skin + roles."""
        cart = self.inventory.get_cartridge(cartridge_id)
        if cart is None:
            raise KeyError(f"Cartridge not found: {cartridge_id}")

        # Load the cartridge
        self.load(cartridge_id)

        # Resolve skin
        effective_skin_id = skin_id or cart.default_skin
        if effective_skin_id:
            skin = self.inventory.get_skin(effective_skin_id)
            if skin is None:
                effective_skin_id = None

        # Apply skin if provided
        if skin_id:
            self.apply_skin(skin_id)

        # Build tool list with skin applied
        skin_obj = self.inventory.get_skin(effective_skin_id) if effective_skin_id else None
        tools: list[dict[str, Any]] = []
        for t in cart.tools:
            desc = t.description
            if skin_obj:
                desc = skin_obj.apply(desc, role="tool")
            tools.append({"name": t.name, "description": desc})

        self.scene = Scene(
            cartridge_id=cart.id,
            cartridge_name=cart.name,
            skin_id=effective_skin_id,
            roles=roles or {},
            tools=tools,
        )
        self._record("scene_build", cartridge_id=cartridge_id, skin_id=effective_skin_id)
        return self.scene

    # ── Status ─────────────────────────────────────────────

    @property
    def active_cartridge(self) -> Cartridge | None:
        if self.active_cartridge_id:
            return self.inventory.get_cartridge(self.active_cartridge_id)
        return None

    @property
    def active_skin(self) -> Skin | None:
        if self.active_skin_id:
            return self.inventory.get_skin(self.active_skin_id)
        return None

    @property
    def error(self) -> str | None:
        return self._error_message

    def status(self) -> dict[str, Any]:
        """Get full status snapshot."""
        cart = self.active_cartridge
        skin = self.active_skin
        return {
            "state": self.state.value,
            "cartridge": cart.summary() if cart else None,
            "skin": skin.summary() if skin else None,
            "scene": self.scene.to_dict() if self.scene else None,
            "error": self._error_message,
        }

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent lifecycle events."""
        return self._history[-limit:]

    # ── Internal ───────────────────────────────────────────

    def _record(self, action: str, **kwargs: Any) -> None:
        self._history.append({
            "action": action,
            "timestamp": time.time(),
            **kwargs,
        })
