"""Cartridge — a self-contained behavior module with tools, onboarding, and skin support."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    """A single tool exposed by a cartridge."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    roles: tuple[str, ...] = ("default",)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolDefinition:
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            input_schema=data.get("inputSchema", data.get("input_schema", {})),
            roles=tuple(data.get("roles", ["default"])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "roles": list(self.roles),
        }


@dataclass(frozen=True)
class OnboardingInfo:
    """Tailored onboarding for a specific audience."""

    greeting: str = ""
    description: str = ""
    tools: tuple[str, ...] = ()
    usage: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> OnboardingInfo:
        if not data:
            return cls()
        return cls(
            greeting=data.get("greeting", ""),
            description=data.get("description", ""),
            tools=tuple(data.get("tools", [])),
            usage=data.get("usage", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "greeting": self.greeting,
            "description": self.description,
            "tools": list(self.tools),
            "usage": self.usage,
        }


@dataclass
class Cartridge:
    """A loaded cartridge — behavior module with tools, onboarding, skin.

    Cartridges are the core unit of behavior in the MCP system. Each one
    is self-contained: it has its own tools, onboarding flow for humans
    and agents, an optional default skin, and a git-repo link for sharing.
    """

    id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    tools: list[ToolDefinition] = field(default_factory=list)
    onboarding: dict[str, OnboardingInfo] = field(default_factory=dict)
    default_skin: str | None = None
    repo: str | None = None
    author: str | None = None
    tags: tuple[str, ...] = ()
    requires: dict[str, Any] = field(default_factory=dict)
    stars: int = 0
    _raw_manifest: dict[str, Any] | None = field(default=None, repr=False)

    # ── Construction ──────────────────────────────────────

    @classmethod
    def from_manifest(cls, manifest: dict[str, Any]) -> Cartridge:
        """Create a Cartridge from a cartridge.json manifest dict."""
        tools = [ToolDefinition.from_dict(t) for t in manifest.get("tools", [])]
        onboarding: dict[str, OnboardingInfo] = {}
        for audience_key in ("human", "agent"):
            if audience_key in manifest.get("onboarding", {}):
                onboarding[audience_key] = OnboardingInfo.from_dict(
                    manifest["onboarding"][audience_key]
                )
        return cls(
            id=manifest["id"],
            name=manifest["name"],
            version=manifest.get("version", "0.1.0"),
            description=manifest.get("description", ""),
            tools=tools,
            onboarding=onboarding,
            default_skin=manifest.get("defaultSkin") or manifest.get("default_skin"),
            repo=manifest.get("repo"),
            author=manifest.get("author"),
            tags=tuple(manifest.get("tags", [])),
            requires=manifest.get("requires", {}),
            stars=manifest.get("stars", 0),
            _raw_manifest=manifest,
        )

    # ── Onboarding ────────────────────────────────────────

    def get_onboarding(self, audience: str = "human") -> OnboardingInfo:
        """Get onboarding info tailored for the given audience.

        Falls back through: requested audience → other audience → generated default.
        """
        if audience in self.onboarding:
            return self.onboarding[audience]
        # Fall back to whichever exists
        for info in self.onboarding.values():
            return info
        return self._default_onboarding(audience)

    def _default_onboarding(self, audience: str) -> OnboardingInfo:
        who = "Agent" if audience == "agent" else "You"
        return OnboardingInfo(
            greeting=f"{who} just plugged in {self.name}.",
            description=self.description,
            tools=tuple(t.name for t in self.tools),
            usage=f"Use the {self.name} cartridge tools via MCP calls.",
        )

    # ── Metadata ──────────────────────────────────────────

    @property
    def tool_names(self) -> list[str]:
        return [t.name for t in self.tools]

    @property
    def manifest(self) -> dict[str, Any]:
        """Return the raw manifest if available, otherwise reconstruct."""
        if self._raw_manifest:
            return self._raw_manifest
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tools": [t.to_dict() for t in self.tools],
            "defaultSkin": self.default_skin,
            "repo": self.repo,
            "author": self.author,
            "tags": list(self.tags),
        }

    def summary(self) -> dict[str, Any]:
        """Compact summary for listing."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tags": list(self.tags),
            "tools": len(self.tools),
            "skin": self.default_skin,
            "repo": self.repo,
            "author": self.author,
            "stars": self.stars,
        }

    def __repr__(self) -> str:
        return f"Cartridge(id={self.id!r}, name={self.name!r}, version={self.version!r})"
