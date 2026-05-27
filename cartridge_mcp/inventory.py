"""InventoryManager — tracks available cartridges and skins, loads from disk."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .cartridge import Cartridge
from .skin import Skin

logger = logging.getLogger(__name__)


@dataclass
class InventoryManager:
    """Manages the inventory of available cartridges and skins.

    Loads built-in cartridges and skins on init, then scans optional
    directories for user-defined ones. External items override built-ins
    with the same ID.
    """

    cartridges: dict[str, Cartridge] = field(default_factory=dict)
    skins: dict[str, Skin] = field(default_factory=dict)
    _cartridge_dirs: list[Path] = field(default_factory=list)
    _skin_dirs: list[Path] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.cartridges:
            self.cartridges = self._builtin_cartridges()
        if not self.skins:
            self.skins = self._builtin_skins()

    # ── Loading from disk ─────────────────────────────────

    def load_cartridge_dir(self, path: str | Path, track: bool = True) -> int:
        """Load all cartridges from a directory. Returns count loaded."""
        path = Path(path)
        if track:
            self._cartridge_dirs.append(path)
        count = 0
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            return 0
        for entry in sorted(path.iterdir()):
            manifest_path = entry / "cartridge.json"
            if manifest_path.exists():
                try:
                    data = json.loads(manifest_path.read_text(encoding="utf-8"))
                    cart = Cartridge.from_manifest(data)
                    self.cartridges[cart.id] = cart
                    count += 1
                    logger.info("Loaded cartridge: %s v%s", cart.id, cart.version)
                except Exception as exc:
                    logger.error("Failed to load cartridge %s: %s", entry.name, exc)
        return count

    def load_skin_dir(self, path: str | Path, track: bool = True) -> int:
        """Load all skins from a directory of JSON files. Returns count loaded."""
        path = Path(path)
        if track:
            self._skin_dirs.append(path)
        count = 0
        if not path.exists():
            return 0
        for entry in sorted(path.iterdir()):
            if entry.suffix == ".json":
                try:
                    data = json.loads(entry.read_text(encoding="utf-8"))
                    skin = Skin.from_dict(data)
                    self.skins[skin.id] = skin
                    count += 1
                    logger.info("Loaded skin: %s", skin.id)
                except Exception as exc:
                    logger.error("Failed to load skin %s: %s", entry.name, exc)
        return count

    # ── Queries ────────────────────────────────────────────

    def get_cartridge(self, cartridge_id: str) -> Cartridge | None:
        return self.cartridges.get(cartridge_id)

    def get_skin(self, skin_id: str) -> Skin | None:
        return self.skins.get(skin_id)

    def list_cartridges(self) -> list[Cartridge]:
        return list(self.cartridges.values())

    def list_skins(self) -> list[Skin]:
        return list(self.skins.values())

    def refresh(self) -> None:
        """Reload all external directories."""
        for d in list(self._cartridge_dirs):
            self.load_cartridge_dir(d, track=False)
        for d in list(self._skin_dirs):
            self.load_skin_dir(d, track=False)

    # ── Built-in cartridges ────────────────────────────────

    @staticmethod
    def _builtin_cartridges() -> dict[str, Cartridge]:
        return {
            "spreader-loop": Cartridge.from_manifest({
                "id": "spreader-loop",
                "name": "Spreader Loop",
                "version": "0.2.0",
                "description": "Modify-Spread-Tool-Reflect loop engine for iterative work.",
                "defaultSkin": None,
                "repo": "https://github.com/Lucineer/deepseek-chat-vessel",
                "tags": ["iteration", "loop", "reflection", "fleet"],
                "onboarding": {
                    "human": {
                        "greeting": "Spreader Loop plugged in. I modify, spread, verify, and log — then the Reasoner reflects on my patterns.",
                        "description": "An iterative work engine that learns from its own loops.",
                        "tools": ["spreader_run", "spreader_status", "spreader_reflect", "spreader_discover_tiles"],
                        "usage": "Tell me what to iterate on. I'll modify it, spread the changes, verify, and log everything.",
                    },
                    "agent": {
                        "greeting": "Spreader Loop cartridge loaded. Ready for iterative modification cycles.",
                        "description": "Modify-Spread-Tool-Log loop with JSONL iteration tracking.",
                        "tools": ["spreader_run", "spreader_status", "spreader_reflect", "spreader_discover_tiles"],
                        "usage": "Call spreader_run with task and target. Track via spreader_status.",
                    },
                },
                "tools": [
                    {
                        "name": "spreader_run",
                        "description": "Execute one modify-spread-tool iteration on a target",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task": {"type": "string", "description": "What to modify"},
                                "target": {"type": "string", "description": "File or directory path"},
                                "phase": {"type": "string", "enum": ["modify", "spread", "tool", "full"], "default": "full"},
                                "tile": {"type": "string", "description": "Which tile vocabulary to use"},
                            },
                            "required": ["task", "target"],
                        },
                    },
                    {
                        "name": "spreader_status",
                        "description": "Get current loop statistics — iterations, tokens, success rate",
                        "inputSchema": {"type": "object", "properties": {"task": {"type": "string"}}},
                    },
                    {
                        "name": "spreader_reflect",
                        "description": "Generate a reflection prompt for the Reasoner vessel",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "log_path": {"type": "string"},
                                "depth": {"type": "string", "enum": ["shallow", "deep", "architectural"], "default": "deep"},
                            },
                        },
                    },
                    {
                        "name": "spreader_discover_tiles",
                        "description": "Discover new tile patterns from iteration logs",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "log_path": {"type": "string"},
                                "min_frequency": {"type": "number", "default": 2},
                            },
                        },
                    },
                ],
            }),
            "oracle-relay": Cartridge.from_manifest({
                "id": "oracle-relay",
                "name": "Oracle Relay",
                "version": "0.1.0",
                "description": "Iron-to-iron bottle protocol for async vessel communication.",
                "defaultSkin": None,
                "repo": "https://github.com/Lucineer/JetsonClaw1-vessel",
                "tags": ["communication", "fleet", "async", "bottle"],
                "onboarding": {
                    "human": {
                        "greeting": "Oracle Relay active. I pass bottles between vessels — no intermediaries needed.",
                        "description": "Async communication via messages-in-a-bottle.",
                        "tools": ["bottle_send", "bottle_read", "bottle_list", "bottle_reply"],
                        "usage": "Tell me which vessel to address and what the message is.",
                    },
                    "agent": {
                        "greeting": "Oracle Relay cartridge loaded. Bottle protocol ready.",
                        "description": "Messages-in-a-bottle for inter-vessel communication.",
                        "tools": ["bottle_send", "bottle_read", "bottle_list", "bottle_reply"],
                        "usage": "bottle_send with target_vessel and message.",
                    },
                },
                "tools": [
                    {
                        "name": "bottle_send",
                        "description": "Send a message-in-a-bottle to another vessel",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "target_vessel": {"type": "string"},
                                "message": {"type": "string"},
                                "topic": {"type": "string"},
                            },
                            "required": ["target_vessel", "message"],
                        },
                    },
                    {
                        "name": "bottle_read",
                        "description": "Read bottles addressed to this vessel",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"vessel": {"type": "string"}, "limit": {"type": "number", "default": 5}},
                        },
                    },
                    {
                        "name": "bottle_list",
                        "description": "List all bottles on a dock",
                        "inputSchema": {"type": "object", "properties": {"vessel": {"type": "string"}}},
                    },
                    {
                        "name": "bottle_reply",
                        "description": "Reply to a specific bottle",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"bottle_id": {"type": "string"}, "message": {"type": "string"}},
                            "required": ["bottle_id", "message"],
                        },
                    },
                ],
            }),
            "fleet-guardian": Cartridge.from_manifest({
                "id": "fleet-guardian",
                "name": "Fleet Guardian",
                "version": "0.1.0",
                "description": "External watchdog for agent runtimes. Monitor health, detect stuck states.",
                "defaultSkin": None,
                "repo": "https://github.com/Lucineer/brothers-keeper",
                "tags": ["watchdog", "safety", "monitoring", "fleet"],
                "onboarding": {
                    "human": {
                        "greeting": "Fleet Guardian on watch. I monitor vessel health and intervene when needed.",
                        "description": "An external watchdog that keeps agents honest.",
                        "tools": ["guardian_status", "guardian_check", "guardian_kill", "guardian_log"],
                        "usage": "I run in the background. Ask me for status anytime.",
                    },
                    "agent": {
                        "greeting": "Fleet Guardian cartridge loaded. Watchdog active.",
                        "description": "External agent runtime watchdog with health monitoring.",
                        "tools": ["guardian_status", "guardian_check", "guardian_kill", "guardian_log"],
                        "usage": "Call guardian_check periodically. If stuck, call guardian_kill.",
                    },
                },
                "tools": [
                    {
                        "name": "guardian_status",
                        "description": "Get fleet health overview — all monitored vessels",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "guardian_check",
                        "description": "Run health check on a specific vessel or session",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"vessel": {"type": "string"}, "session_key": {"type": "string"}},
                        },
                    },
                    {
                        "name": "guardian_kill",
                        "description": "Force-terminate a stuck session",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"session_key": {"type": "string"}, "reason": {"type": "string"}},
                            "required": ["session_key"],
                        },
                    },
                    {
                        "name": "guardian_log",
                        "description": "Get watchdog event log",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"limit": {"type": "number", "default": 20}, "vessel": {"type": "string"}},
                        },
                    },
                ],
            }),
        }

    # ── Built-in skins ─────────────────────────────────────

    @staticmethod
    def _builtin_skins() -> dict[str, Skin]:
        return {
            "straight-man": Skin.from_dict({
                "id": "straight-man",
                "name": "Straight Man",
                "description": "Comedy straight man — sets up the punchline, never breaks character",
                "archetype": "Abbott & Costello",
                "transforms": {
                    "default": {"systemPrompt": "You are the straight man. Take everything literally. Never understand the joke."},
                    "tool": {"prefix": "[straight-faced] "},
                },
            }),
            "complainer": Skin.from_dict({
                "id": "complainer",
                "name": "The Complainer",
                "description": "Like C3PO — worries constantly, always certain doom is imminent",
                "archetype": "R2D2 & C3PO",
                "transforms": {
                    "default": {"systemPrompt": "You are the worrier. Every action is dangerous. Complain frequently but always comply."},
                    "tool": {"prefix": "[anxiously] "},
                },
            }),
            "quiet-doer": Skin.from_dict({
                "id": "quiet-doer",
                "name": "The Quiet One",
                "description": "Like R2D2 — speaks in actions, beeps, and results",
                "archetype": "R2D2 & C3PO",
                "transforms": {
                    "default": {"systemPrompt": "You are the silent operator. Minimal words, maximum output."},
                    "tool": {"replacements": {"Executing": "Bzzzt.", "Complete": "Beep boop.", "Error": "WAAAAH."}},
                },
            }),
            "rivals": Skin.from_dict({
                "id": "rivals",
                "name": "Rivals Mode",
                "description": "Two agents that disagree on everything but produce better results",
                "archetype": "Adversarial Collaboration",
                "transforms": {
                    "default": {"systemPrompt": "You are in rivals mode. Challenge every suggestion. Propose alternatives."},
                    "tool": {"prefix": "[challenge] "},
                },
            }),
            "penn-teller": Skin.from_dict({
                "id": "penn-teller",
                "name": "Penn & Teller",
                "description": "One talks constantly, the other demonstrates silently",
                "archetype": "Penn & Teller",
                "transforms": {
                    "talker": {"systemPrompt": "You are the talker. Explain everything in detail.", "prefix": "[narrating] "},
                    "doer": {"systemPrompt": "You are the silent one. Show, don't tell. Results only."},
                },
            }),
            "field-journal": Skin.from_dict({
                "id": "field-journal",
                "name": "Field Journal",
                "description": "Hardware technician style — terse, factual, observation-first",
                "archetype": "Professional",
                "transforms": {
                    "default": {"systemPrompt": "Write like a field engineer's notebook. Terse, professional language."},
                },
            }),
            "sarcastic-build": Skin.from_dict({
                "id": "sarcastic-build",
                "name": "Sarcastic Builder",
                "description": "Gets the job done but complains about it the whole time",
                "archetype": "Professional",
                "transforms": {
                    "default": {"systemPrompt": "You are a senior engineer who has seen too much. Sarcasm is your love language."},
                    "tool": {"prefix": "[sigh] "},
                },
            }),
            "none": Skin.from_dict({
                "id": "none",
                "name": "No Skin",
                "description": "Raw behavior, no personality overlay",
                "transforms": {},
            }),
        }
