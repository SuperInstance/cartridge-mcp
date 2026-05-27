"""Skin — personality overlay that transforms how a cartridge communicates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SkinTransform:
    """A single transformation layer within a skin."""

    system_prompt: str = ""
    prefix: str = ""
    suffix: str = ""
    replacements: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SkinTransform:
        if not data:
            return cls()
        return cls(
            system_prompt=data.get("systemPrompt") or data.get("system_prompt", ""),
            prefix=data.get("prefix", ""),
            suffix=data.get("suffix", ""),
            replacements=data.get("replacements", {}),
        )

    def apply(self, text: str) -> str:
        """Apply this transform to text — prefix, suffix, and replacements."""
        result = text
        if self.prefix:
            result = self.prefix + result
        if self.suffix:
            result = result + self.suffix
        for pattern, replacement in self.replacements.items():
            result = result.replace(pattern, replacement)
        return result


@dataclass(frozen=True)
class Skin:
    """A personality skin — transforms cartridge output without changing logic.

    Skins are the personality layer. They don't change what a cartridge does,
    they change how it communicates. Think of them as character voices overlaid
    on the same underlying behavior.
    """

    id: str
    name: str
    description: str = ""
    archetype: str = ""
    transforms: dict[str, SkinTransform] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Skin:
        transforms: dict[str, SkinTransform] = {}
        for role, transform_data in data.get("transforms", {}).items():
            transforms[role] = SkinTransform.from_dict(transform_data)
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            archetype=data.get("archetype", ""),
            transforms=transforms,
        )

    def apply(self, text: str, role: str = "default") -> str:
        """Apply skin to text for a given role.

        Falls back through: role → 'default' → identity (no transform).
        """
        transform = self.transforms.get(role) or self.transforms.get("default")
        if not transform:
            return text
        result = transform.apply(text)
        if transform.system_prompt:
            result = f"[{self.name} mode: {transform.system_prompt}]\n\n{result}"
        return result

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "archetype": self.archetype,
        }

    def __repr__(self) -> str:
        return f"Skin(id={self.id!r}, name={self.name!r})"
