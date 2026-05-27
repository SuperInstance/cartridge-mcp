"""HealthMonitor — checks cartridge and system health."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .lifecycle import CartridgeState, LifecycleManager


class HealthStatus(Enum):
    """Overall health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class HealthCheck:
    """Result of a single health check."""

    name: str
    status: HealthStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: float = field(default_factory=time.time)


@dataclass
class HealthMonitor:
    """Monitors the health of the cartridge system.

    Checks cartridge state, inventory integrity, and scene consistency.
    Maintains a log of health checks for diagnostics.
    """

    lifecycle: LifecycleManager
    _checks: list[HealthCheck] = field(default_factory=list)

    def check_all(self) -> HealthCheck:
        """Run all health checks and return an aggregate result."""
        checks = [
            self.check_cartridge_state(),
            self.check_inventory(),
            self.check_scene(),
        ]
        self._checks.extend(checks)

        # Aggregate: worst status wins
        statuses = [c.status for c in checks]
        if HealthStatus.UNHEALTHY in statuses:
            agg = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            agg = HealthStatus.DEGRADED
        elif HealthStatus.HEALTHY in statuses:
            agg = HealthStatus.HEALTHY
        else:
            agg = HealthStatus.UNKNOWN

        return HealthCheck(
            name="system",
            status=agg,
            message=f"{len(checks)} checks: " + ", ".join(f"{c.name}={c.status.value}" for c in checks),
            details={"checks": [{"name": c.name, "status": c.status.value, "message": c.message} for c in checks]},
        )

    def check_cartridge_state(self) -> HealthCheck:
        """Check if the active cartridge is in a good state."""
        state = self.lifecycle.state

        if state == CartridgeState.ACTIVE:
            cart = self.lifecycle.active_cartridge
            if cart is None:
                return HealthCheck(
                    name="cartridge_state",
                    status=HealthStatus.UNHEALTHY,
                    message=f"State is {state.value} but no cartridge found",
                )
            return HealthCheck(
                name="cartridge_state",
                status=HealthStatus.HEALTHY,
                message=f"Cartridge '{cart.id}' is active",
                details={"cartridge": cart.id, "version": cart.version},
            )

        if state == CartridgeState.ERROR:
            return HealthCheck(
                name="cartridge_state",
                status=HealthStatus.UNHEALTHY,
                message=f"Cartridge in error state: {self.lifecycle.error}",
            )

        if state == CartridgeState.EMPTY:
            return HealthCheck(
                name="cartridge_state",
                status=HealthStatus.HEALTHY,
                message="No cartridge loaded (empty state is normal)",
            )

        # LOADING or UNLOADING — transient, consider degraded
        return HealthCheck(
            name="cartridge_state",
            status=HealthStatus.DEGRADED,
            message=f"Cartridge in transient state: {state.value}",
        )

    def check_inventory(self) -> HealthCheck:
        """Check inventory integrity."""
        carts = self.lifecycle.inventory.list_cartridges()
        skins = self.lifecycle.inventory.list_skins()

        if not carts:
            return HealthCheck(
                name="inventory",
                status=HealthStatus.UNHEALTHY,
                message="No cartridges available",
            )

        # Check for cartridges with missing tools
        issues: list[str] = []
        for cart in carts:
            if not cart.tools:
                issues.append(f"Cartridge '{cart.id}' has no tools")

        status = HealthStatus.DEGRADED if issues else HealthStatus.HEALTHY
        return HealthCheck(
            name="inventory",
            status=status,
            message=f"{len(carts)} cartridges, {len(skins)} skins" + (f" — issues: {'; '.join(issues)}" if issues else ""),
            details={"cartridges": len(carts), "skins": len(skins)},
        )

    def check_scene(self) -> HealthCheck:
        """Check scene consistency."""
        scene = self.lifecycle.scene

        if scene is None:
            return HealthCheck(
                name="scene",
                status=HealthStatus.HEALTHY,
                message="No scene active",
            )

        # Verify scene cartridge matches active cartridge
        if scene.cartridge_id != self.lifecycle.active_cartridge_id:
            return HealthCheck(
                name="scene",
                status=HealthStatus.UNHEALTHY,
                message=f"Scene cartridge '{scene.cartridge_id}' != active '{self.lifecycle.active_cartridge_id}'",
            )

        return HealthCheck(
            name="scene",
            status=HealthStatus.HEALTHY,
            message=f"Scene active: {scene.cartridge_name}",
            details={"tools": len(scene.tools), "skin": scene.skin_id},
        )

    def recent_checks(self, limit: int = 10) -> list[HealthCheck]:
        """Get recent health checks."""
        return self._checks[-limit:]
